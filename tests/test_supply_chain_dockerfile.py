"""Supply-chain regression tests for the Provider Dockerfile.

Verifies that the Provider image build uses immutable digests, hash-verified
dependency installation, and binary-only policy consistent with the
supply-chain security policy in SECURITY.md and issue #108 remediation.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

DOCKERFILE = Path(__file__).resolve().parents[1] / "services" / "provider" / "Dockerfile"


class ProviderDockerfileSupplyChainTests(unittest.TestCase):
    """Tests for the Provider Dockerfile supply-chain controls."""

    def setUp(self):
        self.content = DOCKERFILE.read_text(encoding="utf-8")

    def test_base_image_uses_immutable_digest_not_latest_tag(self):
        """Every FROM pin must use @sha256: digest. The digest makes the
        reference immutable regardless of the tag name used for readability."""
        for line in self.content.splitlines():
            stripped = line.strip()
            if not stripped.startswith("FROM"):
                continue
            # Every FROM must pin an immutable sha256 digest
            self.assertRegex(
                stripped,
                r"FROM\s+.+@sha256:[0-9a-f]{64}",
                f"FROM line must pin an immutable sha256 digest, found: {stripped}",
            )
            # A FROM line without @sha256: digest is a mutable tag reference
            self.assertIn(
                "@sha256:",
                stripped,
                f"FROM line must use immutable digest pinning, found: {stripped}",
            )

    def test_no_unpinned_from_lines(self):
        """No FROM line may lack an immutable digest pin."""
        from_lines = [l for l in self.content.splitlines() if l.strip().startswith("FROM")]
        self.assertTrue(from_lines, "Dockerfile must contain FROM lines")
        for line in from_lines:
            self.assertIn("@sha256:", line, f"FROM line missing digest pin: {line.strip()}")

    def test_pip_install_uses_require_hashes(self):
        """pip install must use --require-hashes for dependency integrity."""
        pip_lines = [l for l in self.content.splitlines() if "pip install" in l]
        found_hashes = any("--require-hashes" in l for l in pip_lines)
        self.assertTrue(found_hashes, "pip install must use --require-hashes")

    def test_pip_install_uses_binary_only_policy(self):
        """pip install must use --only-binary=:all: for supply-chain consistency."""
        pip_lines = [l for l in self.content.splitlines() if "pip install" in l]
        found_binary_only = any("--only-binary=:all:" in l for l in pip_lines)
        self.assertTrue(found_binary_only, "pip install must use --only-binary=:all:")

    def test_pyyaml_source_build_exception_is_documented(self):
        """PyYAML is built from source (--no-binary pyyaml) because no
        compatible wheel exists for the Chainguard/Wolfi musl platform.
        This exception is deliberate and documented."""
        pip_lines = [l for l in self.content.splitlines() if "pip install" in l]
        # The --no-binary pyyaml exception must be present (PyYAML has no
        # musl-compatible wheel on PyPI for Chainguard images).
        self.assertTrue(
            any("--no-binary pyyaml" in l for l in pip_lines),
            "PyYAML source-build exception (--no-binary pyyaml) must be present "
            "because no compatible wheel exists for the Wolfi/musl platform.",
        )

    def test_container_runs_as_non_root(self):
        """The runtime stage must use a non-root USER."""
        user_lines = [l.strip() for l in self.content.splitlines() if l.strip().startswith("USER")]
        # Last USER line is the runtime one (build stage uses USER 0:0)
        runtime_user = user_lines[-1]
        self.assertNotEqual(runtime_user, "USER 0:0")
        self.assertNotEqual(runtime_user, "USER root")
        self.assertNotEqual(runtime_user, "USER 0")

    def test_read_only_rootfs_in_compose(self):
        """Compose must configure read_only rootfs for the provider."""
        compose = Path(__file__).resolve().parents[1] / "compose.yaml"
        content = compose.read_text(encoding="utf-8")
        self.assertIn("read_only: true", content)

    def test_no_latest_tag_in_compose_images(self):
        """Compose image references must use immutable digests, not :latest."""
        compose = Path(__file__).resolve().parents[1] / "compose.yaml"
        content = compose.read_text(encoding="utf-8")
        # Find all image references
        image_refs = re.findall(r"image:\s*\$\{?[A-Z_]+\}?[:-][^\s@]+", content)
        for ref in image_refs:
            # After variable substitution, the default value should not use :latest
            self.assertNotIn(":latest", ref, f"Mutable :latest tag found in compose: {ref}")
            self.assertNotIn(":main", ref, f"Mutable :main tag found in compose: {ref}")


if __name__ == "__main__":
    unittest.main()
