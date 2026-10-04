from __future__ import annotations

import re

from .models import ReviewFinding


class StaticReviewer:
    """Deterministic diff reviewer. It does not trust model self-evaluation."""

    SECRET_PATTERNS = (
        re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[=:]\s*['\"][^'\"]{8,}"),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    )
    TEST_WEAKENING_PATTERNS = (
        re.compile(r"^\+.*pytest\.mark\.skip"),
        re.compile(r"^\+.*pytest\.skip\("),
        re.compile(r"^\+.*xfail"),
        re.compile(r"^\+.*#\s*noqa\b"),
    )

    def review(self, diff_text: str, allowed_paths: set[str] | None = None) -> list[ReviewFinding]:
        findings: list[ReviewFinding] = []
        current_path = ""

        for line in diff_text.splitlines():
            if line.startswith("+++ b/"):
                current_path = line[6:]
                if allowed_paths and not any(
                    current_path == p or current_path.startswith(p.rstrip("/") + "/")
                    for p in allowed_paths
                ):
                    findings.append(
                        ReviewFinding(
                            severity="high",
                            category="scope",
                            path=current_path,
                            message=f"changed path outside declared scope: {current_path}",
                        )
                    )
                continue
            if not line.startswith("+") or line.startswith("+++"):
                continue
            for pattern in self.SECRET_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        ReviewFinding(
                            severity="critical",
                            category="secret",
                            path=current_path,
                            message="possible secret introduced by diff",
                        )
                    )
                    break
            for pattern in self.TEST_WEAKENING_PATTERNS:
                if pattern.search(line):
                    findings.append(
                        ReviewFinding(
                            severity="high",
                            category="test_weakening",
                            path=current_path,
                            message="possible test/security weakening introduced",
                        )
                    )
                    break
        return findings


class SecurityGate:
    """Fail closed when deterministic blocking findings exist."""

    def evaluate(self, findings: list[ReviewFinding]) -> tuple[bool, list[ReviewFinding]]:
        blocking = [finding for finding in findings if finding.blocking]
        return (not blocking, blocking)
