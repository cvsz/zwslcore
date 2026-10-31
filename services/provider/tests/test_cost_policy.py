import unittest

from zeaz_provider.cost import CostClass, CostPolicy, cost_allowed, parse_cost_policy


class CostPolicyTests(unittest.TestCase):
    def test_local_only_allows_only_free_local(self):
        self.assertTrue(
            cost_allowed(CostClass.FREE_LOCAL, CostPolicy.LOCAL_ONLY)
        )
        for cost_class in (
            CostClass.FREE_REMOTE,
            CostClass.CUSTOMER_KEY,
            CostClass.PAID_PLATFORM,
            CostClass.UNKNOWN,
        ):
            with self.subTest(cost_class=cost_class):
                self.assertFalse(
                    cost_allowed(cost_class, CostPolicy.LOCAL_ONLY)
                )

    def test_existing_policies_keep_their_semantics(self):
        self.assertTrue(
            cost_allowed(CostClass.FREE_REMOTE, CostPolicy.ZERO_COST_ONLY)
        )
        self.assertFalse(
            cost_allowed(CostClass.UNKNOWN, CostPolicy.PREFER_ZERO_COST)
        )
        self.assertTrue(
            cost_allowed(CostClass.PAID_PLATFORM, CostPolicy.PERMIT_PAID)
        )

    def test_policy_parser_accepts_local_only(self):
        self.assertEqual(
            parse_cost_policy("local_only"),
            CostPolicy.LOCAL_ONLY,
        )

    def test_policy_parser_rejects_unknown_policy(self):
        with self.assertRaises(ValueError):
            parse_cost_policy("ALLOW_EVERYTHING_UNKNOWN")


if __name__ == "__main__":
    unittest.main()
