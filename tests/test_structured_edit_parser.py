import unittest

from services.engineering.runtime import EngineeringRuntime


class StructuredEditParserTests(unittest.TestCase):
    def test_extracts_json_object_from_model_prose(self):
        raw = 'prefix {"changes":[{"path":"services/example.py","content":"x = 1"}]} suffix'
        self.assertEqual(
            EngineeringRuntime._parse_changes(raw),
            [{"path": "services/example.py", "content": "x = 1"}],
        )

    def test_rejects_empty_response(self):
        with self.assertRaisesRegex(ValueError, "empty edit response"):
            EngineeringRuntime._parse_changes("   ")


if __name__ == "__main__":
    unittest.main()
