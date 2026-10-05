from __future__ import annotations

import unittest

from scripts.github_admin import REQUIRED_CHECKS, protection_payload


class GitHubAdminPolicyTests(unittest.TestCase):
    def test_required_checks_cover_repository_and_security_workflows(self):
        self.assertEqual(
            REQUIRED_CHECKS,
            (
                "repository-baseline",
                "Analyze GitHub Actions",
                "dependency-review",
                "CodeQL",
                "build-scan-sbom",
                "windows-installer",
            ),
        )

    def test_protection_payload_keeps_review_and_branch_safeguards(self):
        payload = protection_payload()

        self.assertTrue(payload["required_status_checks"]["strict"])
        self.assertEqual(
            payload["required_status_checks"]["contexts"], list(REQUIRED_CHECKS)
        )
        self.assertEqual(
            payload["required_pull_request_reviews"][
                "required_approving_review_count"
            ],
            1,
        )
        self.assertTrue(
            payload["required_pull_request_reviews"]["dismiss_stale_reviews"]
        )
        self.assertTrue(
            payload["required_pull_request_reviews"]["require_code_owner_reviews"]
        )
        self.assertTrue(
            payload["required_pull_request_reviews"]["require_last_push_approval"]
        )
        self.assertTrue(payload["enforce_admins"])
        self.assertTrue(payload["required_conversation_resolution"])
        self.assertFalse(payload["allow_force_pushes"])
        self.assertFalse(payload["allow_deletions"])


if __name__ == "__main__":
    unittest.main()
