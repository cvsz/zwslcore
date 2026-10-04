from __future__ import annotations

import json
import shlex
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from collections.abc import Callable
from typing import Any

from .evidence import EvidenceExporter
from .models import Checkpoint, EngineeringTask, TaskStatus
from .review import SecurityGate, StaticReviewer
from .snapshot import RepositorySnapshotter
from .store import SQLiteEngineeringStore
from .validation import evaluate_validation, validate_mode
from .worktree import WorktreeManager


class ProviderClient:
    """Minimal OpenAI-compatible client for the local zwslcore Provider."""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:8080/v1",
        api_key: str = "",
        model: str = "zeaz-fast",
        timeout: int = 300,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def _request_json(
        self,
        request: urllib.request.Request,
        *,
        timeout: int | None = None,
    ) -> dict[str, Any]:
        try:
            with urllib.request.urlopen(request, timeout=timeout or self.timeout) as response:
                value = json.load(response)
        except urllib.error.HTTPError as exc:
            body = exc.read(8192).decode("utf-8", errors="replace").strip()
            detail = body or exc.reason or "no response body"
            raise RuntimeError(
                f"provider HTTP {exc.code} for {request.full_url}: {detail[:4000]}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"provider request failed for {request.full_url}: {exc.reason}"
            ) from exc
        if not isinstance(value, dict):
            raise RuntimeError(f"provider returned non-object JSON for {request.full_url}")
        return value

    def _chat_body(
        self,
        prompt: str,
        system: str,
        *,
        max_tokens: int,
        response_schema: dict[str, Any] | None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": max_tokens,
        }
        if response_schema is not None:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "engineering_changes",
                    "strict": True,
                    "schema": response_schema,
                },
            }
        return body

    def preflight(self) -> None:
        health_url = self.base_url.removesuffix("/v1") + "/health/ready"
        health = self._request_json(
            urllib.request.Request(
                health_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                method="GET",
            ),
            timeout=min(self.timeout, 15),
        )
        if health.get("status") not in {None, "ok", "ready", "healthy"}:
            raise RuntimeError(f"provider readiness failed: {health}")

        models = self._request_json(
            urllib.request.Request(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                method="GET",
            ),
            timeout=min(self.timeout, 15),
        )
        ids = {
            item.get("id")
            for item in models.get("data", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        if self.model not in ids:
            raise RuntimeError(
                f"engineering model '{self.model}' is not advertised by provider; "
                f"available={sorted(ids)}"
            )

    def chat(
        self,
        prompt: str,
        system: str,
        *,
        max_tokens: int = 2048,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        payload = json.dumps(
            self._chat_body(
                prompt,
                system,
                max_tokens=max_tokens,
                response_schema=response_schema,
            )
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
        value = self._request_json(req)
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
    EDIT_RESPONSE_SCHEMA: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["changes"],
        "properties": {
            "changes": {
                "type": "array",
                "maxItems": MAX_CHANGED_FILES,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["path", "content"],
                    "properties": {
                        "path": {"type": "string", "minLength": 1},
                        "content": {"type": "string"},
                    },
                },
            }
        },
    }

    def __init__(
        self,
        store: SQLiteEngineeringStore,
        provider: ProviderClient,
        *,
        worktrees: WorktreeManager | None = None,
        progress: Callable[[str], None] | None = None,
        evidence: EvidenceExporter | None = None,
    ) -> None:
        self.store = store
        self.provider = provider
        self.worktrees = worktrees or WorktreeManager()
        self.reviewer = StaticReviewer()
        self.gate = SecurityGate()
        self.progress = progress or (lambda message: None)
        self.evidence = evidence or EvidenceExporter(store)

    def run(
        self,
        task: EngineeringTask,
        *,
        validators: list[str] | None = None,
        allowed_paths: set[str] | None = None,
        commit: bool = False,
        resume: bool = False,
        validation_mode: str = "strict",
    ) -> EngineeringTask:
        validators = validators or ["git diff --check"]
        validation_mode = validate_mode(validation_mode)
        task.metadata["run_config"] = {
            "validators": list(validators),
            "allowed_paths": sorted(allowed_paths or ()),
            "commit": bool(commit),
            "validation_mode": validation_mode,
        }
        self.store.save_task(task)

        try:
            task.status = TaskStatus.BASELINING
            self.store.save_task(task)
            self.progress(f"[engineering] {task.id} BASELINING")
            self.progress(f"[engineering] {task.id} PROVIDER_PREFLIGHT model={self.provider.model}")
            self.provider.preflight()
            self.progress(f"[engineering] {task.id} PROVIDER_PREFLIGHT_PASS")

            if resume and task.worktree_path and Path(task.worktree_path).exists():
                previous_head, source_head = self.worktrees.sync_to_source(
                    task.repository,
                    task.worktree_path,
                )
                worktree = Path(task.worktree_path).resolve()
                branch = task.branch_name or self.worktrees.safe_branch_name(task.id, task.title)
                task.metadata["resume_previous_head"] = previous_head
                task.metadata["resume_source_head"] = source_head
                self.store.save_task(task)
                self.progress(
                    f"[engineering] RESUME_WORKTREE worktree={worktree} branch={branch} "
                    f"previous_head={previous_head[:12]} source_head={source_head[:12]}"
                )
                if previous_head != source_head:
                    self.progress(
                        f"[engineering] WORKTREE_SYNC old={previous_head[:12]} new={source_head[:12]}"
                    )
            else:
                worktree, branch = self.worktrees.create(task.repository, task.id, task.title)
                task.worktree_path = str(worktree)
                task.branch_name = branch
                self.progress(f"[engineering] worktree={worktree} branch={branch}")

            baseline_head = self._git(worktree, ["rev-parse", "HEAD"], capture=True).strip()
            task.metadata["baseline_head"] = baseline_head

            task.attempts += 1
            self.progress(f"[engineering] attempt={task.attempts}/{task.max_attempts}")
            self._checkpoint(
                task,
                "BASELINE",
                {"worktree": str(worktree), "branch": branch, "head": baseline_head},
            )

            baseline_validation = None
            if validation_mode == "delta":
                self.progress(
                    f"[engineering] {task.id} BASELINE_VALIDATING validators={len(validators)}"
                )
                baseline_validation = self._run_validators(worktree, validators)
                baseline_validation["mode"] = "baseline"
                self._checkpoint(task, "BASELINE_VALIDATION", baseline_validation)
                self.progress(
                    f"[engineering] {task.id} BASELINE_VALIDATION_COMPLETE "
                    f"failures={len(baseline_validation.get('failures') or [])}"
                )

            task.status = TaskStatus.PLANNING
            self.store.save_task(task)
            self.progress(f"[engineering] {task.id} PLANNING model={self.provider.model}")
            snapshot = RepositorySnapshotter(
                worktree,
                include_paths=allowed_paths,
            ).snapshot()
            self.progress(
                f"[engineering] snapshot_bytes={len(snapshot.encode('utf-8'))} "
                f"scope={','.join(sorted(allowed_paths)) if allowed_paths else 'repository'}"
            )
            candidates = self._snapshot_candidate_paths(snapshot)
            self.progress(
                f"[engineering] candidate_files={len(candidates)} "
                f"sample={','.join(candidates[:6]) if candidates else 'none'}"
            )
            plan_checkpoint = self.store.latest_checkpoint(task.id, "PLAN") if resume else None
            reusable_plan = ""
            if plan_checkpoint is not None:
                checkpoint_head = str(plan_checkpoint.payload.get("baseline_head", ""))
                candidate_plan = plan_checkpoint.payload.get("plan")
                if (
                    isinstance(candidate_plan, str)
                    and candidate_plan.strip()
                    and checkpoint_head == baseline_head
                ):
                    reusable_plan = candidate_plan

            if reusable_plan:
                plan = reusable_plan
                self.progress(
                    f"[engineering] RESUME_PLAN checkpoint={plan_checkpoint.id} head={baseline_head[:12]}"
                )
            else:
                plan = self.provider.chat(
                    self._plan_prompt(task, snapshot),
                    "You are a careful senior software engineer. Plan a minimal, testable change. "
                    "Never request secret files, credential access, remote pushes, or test weakening.",
                    max_tokens=1200,
                )
                self._checkpoint(
                    task,
                    "PLAN",
                    {"plan": plan[:12000], "baseline_head": baseline_head},
                )

            task.status = TaskStatus.EDITING
            self.store.save_task(task)
            self.progress(f"[engineering] {task.id} EDITING")
            response = self.provider.chat(
                self._edit_prompt(task, snapshot, plan, allowed_paths, candidates),
                "Return ONLY valid JSON with schema "
                '{"changes":[{"path":"relative/path","content":"complete UTF-8 file content"}]}. '
                "Use the smallest safe diff. Never include secrets, .env files, private keys, "
                "generated/vendor files, or files outside the repository.",
                max_tokens=4096,
                response_schema=self.EDIT_RESPONSE_SCHEMA,
            )
            try:
                changes = self._parse_changes(response)
            except (json.JSONDecodeError, ValueError) as exc:
                self.progress(
                    f"[engineering] edit_response_invalid error={str(exc)[:300]} "
                    f"raw={self._safe_snippet(response)}"
                )
                self._checkpoint(
                    task,
                    "EDIT_RESPONSE_INVALID",
                    {
                        "error": str(exc)[:1000],
                        "raw_snippet": self._safe_snippet(response, 2000),
                    },
                )
                repaired = self.provider.chat(
                    self._repair_prompt(response, allowed_paths, candidates),
                    "Convert the supplied model output into ONLY valid JSON with schema "
                    '{"changes":[{"path":"relative/path","content":"complete UTF-8 file content"}]}. '
                    "Do not add commentary, Markdown fences, explanations, or new changes.",
                    max_tokens=4096,
                    response_schema=self.EDIT_RESPONSE_SCHEMA,
                )
                try:
                    changes = self._parse_changes(repaired)
                except (json.JSONDecodeError, ValueError) as repair_exc:
                    raise ValueError(
                        "model edit response was not valid structured JSON after one repair: "
                        f"initial={str(exc)[:300]}; repair={str(repair_exc)[:300]}; "
                        f"initial_raw={self._safe_snippet(response)}; "
                        f"repair_raw={self._safe_snippet(repaired)}"
                    ) from repair_exc
                self.progress("[engineering] EDIT_RESPONSE_REPAIRED")
                self._checkpoint(
                    task,
                    "EDIT_RESPONSE_REPAIRED",
                    {"raw_snippet": self._safe_snippet(repaired, 2000)},
                )
            if not changes or not self._changes_within_scope(changes, allowed_paths):
                reason = "no file changes" if not changes else "out-of-scope paths"
                self.progress(f"[engineering] edit_regenerate reason={reason}")
                regenerated = self.provider.chat(
                    self._regenerate_prompt(
                        task,
                        snapshot,
                        plan,
                        allowed_paths,
                        candidates,
                        reason,
                    ),
                    "Return ONLY valid JSON with schema "
                    '{"changes":[{"path":"relative/path","content":"complete UTF-8 file content"}]}. '
                    "You MUST produce at least one concrete file change inside the allowed scope. "
                    "Do not include commentary or Markdown fences.",
                    max_tokens=4096,
                    response_schema=self.EDIT_RESPONSE_SCHEMA,
                )
                changes = self._parse_changes(regenerated)
                self._checkpoint(
                    task,
                    "EDIT_RESPONSE_REGENERATED",
                    {
                        "reason": reason,
                        "raw_snippet": self._safe_snippet(regenerated, 2000),
                    },
                )
                self.progress(
                    f"[engineering] EDIT_RESPONSE_REGENERATED proposed_files={len(changes)}"
                )

            self.progress(f"[engineering] proposed_files={len(changes)}")
            self._apply_changes(worktree, changes, allowed_paths=allowed_paths)

            task.status = TaskStatus.VALIDATING
            self.store.save_task(task)
            self.progress(f"[engineering] {task.id} VALIDATING validators={len(validators)}")
            final_validation = self._run_validators(worktree, validators)
            validation = evaluate_validation(
                baseline_validation,
                final_validation,
                mode=validation_mode,
            )
            self._checkpoint(task, "VALIDATION", validation)
            if not validation["passed"]:
                blocking = validation["regressions"] if validation_mode == "delta" else validation["failures"]
                self.progress(
                    f"[engineering] validation_failed mode={validation_mode} blocking={blocking}"
                )
                raise RuntimeError(
                    f"validation {validation_mode} failed: " + "; ".join(blocking)
                )
            self.progress(
                f"[engineering] {task.id} VALIDATION_PASS mode={validation_mode} "
                f"residual={len(validation.get('residual_failures') or [])} "
                f"improvements={len(validation.get('improvements') or [])}"
            )

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
            self._export_evidence(task)
            return task
        except Exception as exc:
            task.status = TaskStatus.BLOCKED if task.attempts < task.max_attempts else TaskStatus.FAILED
            self.progress(f"[engineering] {task.id} {task.status.value} error={str(exc)[:500]}")
            task.last_error = str(exc)[:2000]
            self.store.save_task(task)
            self._checkpoint(task, "FAILED", {"error": task.last_error})
            self._export_evidence(task)
            raise

    @staticmethod
    def _plan_prompt(task: EngineeringTask, snapshot: str) -> str:
        return (
            f"Task: {task.title}\nDescription: {task.description}\nRisk: {task.risk.value}\n"
            "Produce a concise implementation plan with validation steps.\n\n"
            f"Repository snapshot:\n{snapshot}"
        )

    @staticmethod
    def _scope_instruction(allowed_paths: set[str] | None) -> str:
        if not allowed_paths:
            return (
                "Paths must be repository-relative and must not include a repository-name prefix."
            )
        allowed = ", ".join(sorted(path.rstrip("/") for path in allowed_paths))
        return (
            "Every change path MUST be repository-relative, MUST NOT include the repository name "
            f"as a prefix, and MUST be inside one of these allowed path prefixes: {allowed}. "
            "Do not propose README.md, docs, or any other path outside that scope."
        )

    @staticmethod
    def _candidate_instruction(candidates: list[str]) -> str:
        if not candidates:
            return "Candidate files: none discovered from the scoped snapshot."
        return "Candidate files from the scoped snapshot: " + ", ".join(candidates[:24])

    @classmethod
    def _edit_prompt(
        cls,
        task: EngineeringTask,
        snapshot: str,
        plan: str,
        allowed_paths: set[str] | None,
        candidates: list[str],
    ) -> str:
        return (
            f"Task: {task.title}\nDescription: {task.description}\n"
            f"Scope rule: {cls._scope_instruction(allowed_paths)}\n"
            f"{cls._candidate_instruction(candidates)}\n"
            "Prefer modifying one of the candidate files. Use a new file only when required. "
            "You MUST return at least one concrete change when the task requires implementation.\n"
            f"Plan:\n{plan}\n\nRepository snapshot:\n{snapshot}"
        )

    @classmethod
    def _repair_prompt(
        cls,
        raw: str,
        allowed_paths: set[str] | None,
        candidates: list[str],
    ) -> str:
        return (
            "The following edit response did not satisfy the required JSON schema and/or path policy. "
            "Preserve only intended file changes that comply with the scope rule. "
            f"Scope rule: {cls._scope_instruction(allowed_paths)}\n"
            f"{cls._candidate_instruction(candidates)}\n"
            "Return only schema-valid JSON. Drop changes outside scope, but do not return an empty "
            "changes list when a valid scoped candidate can satisfy the task.\n\n"
            f"RAW RESPONSE:\n{raw[:12000]}"
        )

    @classmethod
    def _regenerate_prompt(
        cls,
        task: EngineeringTask,
        snapshot: str,
        plan: str,
        allowed_paths: set[str] | None,
        candidates: list[str],
        reason: str,
    ) -> str:
        return (
            f"Task: {task.title}\nDescription: {task.description}\n"
            f"Previous structured edit was unusable because: {reason}.\n"
            f"Scope rule: {cls._scope_instruction(allowed_paths)}\n"
            f"{cls._candidate_instruction(candidates)}\n"
            "Generate a fresh minimal implementation now. Prefer an existing candidate file and "
            "return at least one change.\n"
            f"Plan:\n{plan}\n\nRepository snapshot:\n{snapshot}"
        )

    @staticmethod
    def _snapshot_candidate_paths(snapshot: str) -> list[str]:
        prefix = "--- FILE: "
        candidates: list[str] = []
        for line in snapshot.splitlines():
            stripped = line.strip()
            if not stripped.startswith(prefix) or not stripped.endswith(" ---"):
                continue
            path = stripped[len(prefix):-4].strip()
            if path and path not in candidates:
                candidates.append(path)
        return candidates

    @staticmethod
    def _changes_within_scope(
        changes: list[dict[str, str]],
        allowed_paths: set[str] | None,
    ) -> bool:
        if not allowed_paths:
            return True
        for change in changes:
            path = change.get("path", "")
            if not any(
                path == allowed or path.startswith(allowed.rstrip("/") + "/")
                for allowed in allowed_paths
            ):
                return False
        return True

    @staticmethod
    def _safe_snippet(raw: str, limit: int = 500) -> str:
        return " ".join(raw.strip().split())[:limit]

    @staticmethod
    def _parse_changes(raw: str) -> list[dict[str, str]]:
        text = raw.strip()
        if not text:
            raise ValueError("model returned an empty edit response")

        fence = chr(96) * 3
        if text.startswith(fence):
            lines = text.splitlines()
            text = "\n".join(lines[1:-1] if lines[-1].strip() == fence else lines[1:]).strip()

        value: Any
        try:
            value = json.loads(text)
        except json.JSONDecodeError as initial_error:
            decoder = json.JSONDecoder()
            value = None
            for index, character in enumerate(text):
                if character != "{":
                    continue
                try:
                    candidate, _ = decoder.raw_decode(text[index:])
                except json.JSONDecodeError:
                    continue
                if isinstance(candidate, dict) and "changes" in candidate:
                    value = candidate
                    break
            if value is None:
                raise initial_error

        if not isinstance(value, dict):
            raise ValueError("model response must be a JSON object")
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
        checkpoint = Checkpoint(task_id=task.id, phase=phase, payload=payload)
        self.store.save_checkpoint(checkpoint)
        task.metadata["phase_cursor"] = phase
        task.metadata["phase_checkpoint_id"] = checkpoint.id
        self.store.save_task(task)

    def _export_evidence(self, task: EngineeringTask) -> None:
        try:
            path, digest = self.evidence.export(task)
        except Exception as exc:
            task.metadata["evidence_error"] = str(exc)[:500]
            self.store.save_task(task)
            self.progress(f"[engineering] EVIDENCE_WRITE_FAILED error={str(exc)[:300]}")
            return
        task.metadata["evidence_path"] = str(path)
        task.metadata["evidence_sha256"] = digest
        task.metadata.pop("evidence_error", None)
        self.store.save_task(task)
        self.progress(f"[engineering] EVIDENCE_WRITTEN sha256={digest[:16]} path={path}")

    @staticmethod
    def _git(root: Path, args: list[str], *, capture: bool = False) -> str:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            text=True,
            capture_output=capture,
        )
        return proc.stdout if capture else ""
