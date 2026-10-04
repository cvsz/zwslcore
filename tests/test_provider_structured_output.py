from __future__ import annotations

import unittest

from services.provider.zeaz_provider.providers import (
    _ollama_chat_to_openai,
    _ollama_structured_payload,
    _structured_schema,
)


class NativeOllamaStructuredOutputTests(unittest.TestCase):
    def test_extracts_json_schema(self):
        schema = {"type": "object", "required": ["status"], "properties": {"status": {"type": "string"}}}
        payload = {
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "status", "strict": True, "schema": schema},
            }
        }
        self.assertEqual(_structured_schema(payload), schema)

    def test_builds_native_ollama_format_request(self):
        schema = {"type": "object", "required": ["status"], "properties": {"status": {"type": "string"}}}
        value = _ollama_structured_payload(
            {
                "model": "qwen2.5-coder:3b",
                "messages": [{"role": "user", "content": "Return status OK"}],
                "temperature": 0,
                "top_p": 0.9,
                "max_tokens": 128,
            },
            schema,
        )
        self.assertEqual(value["format"], schema)
        self.assertFalse(value["stream"])
        self.assertEqual(value["options"]["temperature"], 0)
        self.assertEqual(value["options"]["top_p"], 0.9)
        self.assertEqual(value["options"]["num_predict"], 128)

    def test_normalizes_native_response_to_openai(self):
        value = _ollama_chat_to_openai(
            {
                "message": {"role": "assistant", "content": '{"status":"OK"}'},
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 10,
                "eval_count": 4,
            },
            "qwen2.5-coder:3b",
        )
        self.assertEqual(value["choices"][0]["message"]["content"], '{"status":"OK"}')
        self.assertEqual(value["usage"]["total_tokens"], 14)
        self.assertEqual(value["model"], "qwen2.5-coder:3b")


if __name__ == "__main__":
    unittest.main()
