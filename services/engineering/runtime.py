from __future__ import annotations

import json
import shlex
import subprocess
import urllib.request
from pathlib import Path
from collections.abc import Callable
from typing import Any

from .models import Checkpoint, EngineeringTask, TaskStatus
from .review import SecurityGate, StaticReviewer
from .snapshot import RepositorySnapshotter
from .store import SQLiteEngineeringStore
from .worktree import WorktreeManager


class ProviderClient:
    """Minimal OpenAI-compatible client for the local zwslcore Provider."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080/v1",
        api_key: str = "",
        model: str = "zeaz-local",
        timeout: int = 300,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def chat(self, prompt: str, system: str) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0,
            }
        ).encode()
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            value = json.load(response)
        choices = value.get("choices") or []
        if not choices:
            raise RuntimeError("provider returned no choices")
        content = choices[0].get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError("provider returned empty content")
        return content


class EngineeringRuntime:
    """Bounded local engineering execution over isolated Git worktrees."""

    MAX_CHANGED_FILES = 12
    MAX_FILE_BYTES = 256 * 1024

    def __init__(
        self,
        store: SQLiteEngineeringStore,
        provider: ProviderClient,
        *,
        worktrees: WorktreeManager | None = None,
        progress: Callable[[str], None] | None = None,
    ) -> None:
        self.store = store
        self.provider = provider
        self.worktrees = worktrees or WorktreeManager()
        self.reviewer = StaticReviewer()
        self.gate = SecurityGate()
        self.progress = progress or (lambda message: None)

    def run(
        self,
        task: EngineeringTask,
        *,
        validators: list[str] | None = None,
        allowed_paths: set[str] | None = None,
        commit: bool = False,
    ) -> EngineeringTask:
        validators = validators or ["git diff --check"]
        self.store.save_task(task)

        try:
            task.status = TaskStatus.BASELINING
            self.store.save_task(task)
            self.progress(f"[engineering] {task.id} BASELINING")
            worktree, branch = self.worktrees.create(task.repository, task.id, task.title)
            task.worktree_path = str(worktree)
            task.branch_name = branch
            task.attempts += 1
            self.progress(f"[engineering] worktree={worktree} branch={branch} attempt={task.attempts}/{task.max_attempts}")
            self._checkpoint(task, "BASELINE", {"worktree": str(worktree), "branch": branch})

            task.status = TaskStatus.PLANNING
            self.store.save_task(task)
            self.progress(f"[engineering] {task.id} PLANNING model={self.provider.model}")
            snapshot = RepositorySnapshotter(worktree).snapshot()
            plan = self.provider.chat(
                self._plan_prompt(task, snapshot),
                "You are a careful senior software engineer. Plan a minimal, testable change. "
                "Never request secret files, credential access, remote pushes, or test weakening.",
            )
            self._checkpoint(task, "PLAN", {"plan": plan[:12000]})

            task.status = TaskStatus.EDITING
            self.store.save_task(task)
            self.progress(f"[engineering] {task.id} EDITING")
            response = self.provider.chat(
                self._edit_prompt(task, snapshot, plan),
                "Return ONLY valid JSON with schema "
                '{"changes":[{"path":"relative/path","content":"complete UTF-8 file content"}]}. '
                "Use the smallest safe diff. Never include secrets, .env files, private keys, "
                "generated/vendor files, or files outside the repository.",
            )
            changes = self._parse_changes(response)
            self.progress(f"[engineering] proposed_files={len(changes)}")
            self._apply_changes(worktree, changes, allowed_paths=allowed_paths)

            task.status = TaskStatus.VALIDATING
            self.store.save_task(task)
            self.progress(f"[engineering] {task.id} VALIDATING validators={len(validators)}")
            validation = self._run_validators(worktree, validators)
            self._checkpoint(task, "VALIDATION", validation)
            if not validation["passed"]:
                self.progress(f"[engineering] validation_failed={validation['failures']}")
                raise RuntimeError("validation failed: " + "; ".join(validation["failures"]))
            self.progress(f"[engineering] {task.id} VALIDATION_PASS")

            task.status = TaskStatus.REVIEWING
            self.store.save_task(task)
            self.progress(f"[engineering] {task.id} REVIEWING")
            # Intent-to-add makes new files visible to the deterministic diff reviewer
            # without staging their content for commit.
            self._git(worktree, ["add", "-N", "--", "."])
            diff = self._git(worktree, ["diff", "--no-ext-diff", "--binary"], capture=True)
            findings = self.reviewer.review(diff, allowed_paths=allowed_paths)
            passed, blocking = self.gate.evaluate(findings)
            self._checkpoint(
                task,
                "REVIEW",
                {"findings": [finding.__dict__ for finding in findings]},
            )
            if not passed:
                self.progress(f"[engineering] security_gate_blocked={len(blocking)}")
                raise RuntimeError(
                    "security gate blocked change: "
                    + "; ".join(f"{f.category}:{f.path}" for f in blocking)
                )

            self.progress(f"[engineering] {task.id} SECURITY_GATE_PASS findings={len(findings)}")

            if commit:
                self._git(worktree, ["add", "-A"])
                self._git(worktree, ["commit", "-m", f"engineering: {task.title[:72]}"])
                self._checkpoint(task, "COMMIT", {"branch": task.branch_name})
                self.progress(f"[engineering] {task.id} COMMITTED branch={task.branch_name}")
            else:
                # Clear intent-to-add entries while preserving working-tree edits.
                self._git(worktree, ["reset"])

            task.status = TaskStatus.SUCCEEDED
            task.last_error = ""
            self.progress(f"[engineering] {task.id} SUCCEEDED")
            self.store.save_task(task)
            return task
        except Exception as exc:
            task.status = TaskStatus.BLOCKED if task.attempts < task.max_attempts else TaskStatus.FAILED
            self.progress(f"[engineering] {task.id} {task.status.value} error={str(exc)[:500]}")
            task.last_error = str(exc)[:2000]
            self.store.save_task(task)
            self._checkpoint(task, "FAILED", {"error": task.last_error})
            raise

    @staticmethod
    def _plan_prompt(task: EngineeringTask, snapshot: str) -> str:
        return (
            f"Task: {task.title}\nDescription: {task.description}\nRisk: {task.risk.value}\n"
            "Produce a concise implementation plan with validation steps.\n\n"
            f"Repository snapshot:\n{snapshot}"
        )

    @staticmethod
    def _edit_prompt(task: EngineeringTask, snapshot: str, plan: str) -> str:
        return (
            f"Task: {task.title}\nDescription: {task.description}\n"
            f"Plan:\n{plan}\n\nRepository snapshot:\n{snapshot}"
        )

    @staticmethod
    def _parse_changes(raw: str) -> list[dict[str, str]]:
        text = raw.strip()
        fence = chr(96) * 3
        if text.startswith(fence):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == fence else lines[1:])
        value = json.loads(text)
        changes = value.get("changes")
        if not isinstance(changes, list):
            raise ValueError("model response must contain changes[]")
        normalized: list[dict[str, str]] = []
        for change in changes:
            if not isinstance(change, dict):
                raise ValueError("each change must be an object")
            path = change.get("path")
            file_content = change.get("content")
            if not isinstance(path, str) or not isinstance(file_content, str):
                raise ValueError("change path/content must be strings")
            normalized.append({"path": path, "content": file_content})
        return normalized

    def _apply_changes(
        self,
        root: Path,
        changes: list[dict[str, str]],
        *,
        allowed_paths: set[str] | None,
    ) -> None:
        if not changes:
            raise ValueError("model proposed no file changes")
        if len(changes) > self.MAX_CHANGED_FILES:
            raise ValueError(f"model proposed too many files: {len(changes)}")

        for change in changes:
            rel = Path(change["path"])
            if rel.is_absolute() or ".." in rel.parts:
                raise ValueError(f"unsafe path: {rel}")
            rel_posix = rel.as_posix()
            if rel_posix.startswith(".env") or rel.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}:
                raise ValueError(f"secret-bearing path is forbidden: {rel}")
            if allowed_paths and not any(
                rel_posix == p or rel_posix.startswith(p.rstrip("/") + "/")
                for p in allowed_paths
            ):
                raise ValueError(f"path outside declared scope: {rel}")
            encoded = change["content"].encode("utf-8")
            if len(encoded) > self.MAX_FILE_BYTES:
                raise ValueError(f"file too large: {rel}")
            target = (root / rel).resolve()
            target.relative_to(root.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(encoded)

    @staticmethod
    def _run_validators(root: Path, validators: list[str]) -> dict[str, Any]:
        failures: list[str] = []
        results: list[dict[str, Any]] = []
        for command in validators:
            argv = shlex.split(command)
            if not argv:
                continue
            proc = subprocess.run(
                argv,
                cwd=root,
                text=True,
                capture_output=True,
                timeout=600,
            )
            item = {
                "command": command,
                "returncode": proc.returncode,
                "stdout": proc.stdout[-8000:],
                "stderr": proc.stderr[-8000:],
            }
            results.append(item)
            if proc.returncode != 0:
                failures.append(command)
        return {"passed": not failures, "failures": failures, "results": results}

    def _checkpoint(self, task: EngineeringTask, phase: str, payload: dict[str, Any]) -> None:
        self.store.save_checkpoint(Checkpoint(task_id=task.id, phase=phase, payload=payload))

    @staticmethod
    def _git(root: Path, args: list[str], *, capture: bool = False) -> str:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            text=True,
            capture_output=capture,
        )
        return proc.stdout if capture else ""
