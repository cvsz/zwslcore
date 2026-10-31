"""OpenAI and Anthropic contract checks against an in-memory upstream transport."""
from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import httpx

from zeaz_provider.config import ModelRoute, ProviderConfig, RouteTarget, Settings
from zeaz_provider.main import app
from zeaz_provider.router import ProviderRouter
from zeaz_provider.security import client_key_digest


CLIENT_KEY = "contract-test-client-key"


def _chat_response(model: str, *, tool_call: bool = False) -> dict:
    message = {"role": "assistant", "content": None if tool_call else "ok"}
    if tool_call:
        message["tool_calls"] = [{
            "id": "call_test",
            "type": "function",
            "function": {"name": "lookup", "arguments": "{}"},
        }]
    return {
        "id": "chatcmpl_test",
        "object": "chat.completion",
        "created": 1,
        "model": model,
        "choices": [{"index": 0, "message": message,
                     "finish_reason": "tool_calls" if tool_call else "stop"}],
        "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
    }


class ProviderApiContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls: list[tuple[str, dict, httpx.Headers]] = []
        self.settings = Settings(
            providers={
                "openai": ProviderConfig(
                    name="openai", api="openai", base_url="https://openai.example/v1",
                    api_key="upstream-openai-test-key", cost_class="FREE_LOCAL", max_attempts=1,
                    retry_base_seconds=0, retry_max_seconds=0,
                ),
                "anthropic": ProviderConfig(
                    name="anthropic", api="anthropic", base_url="https://anthropic.example/v1",
                    api_key="upstream-anthropic-test-key", cost_class="FREE_REMOTE", max_attempts=1,
                    retry_base_seconds=0, retry_max_seconds=0,
                ),
                "responses": ProviderConfig(
                    name="responses", api="responses", base_url="https://responses.example/v1",
                    api_key="upstream-responses-test-key", cost_class="FREE_REMOTE", max_attempts=1,
                    retry_base_seconds=0, retry_max_seconds=0,
                ),
            },
            models={
                "chat-local": ModelRoute("chat-local", RouteTarget("openai", "upstream-chat")),
                "anthropic-local": ModelRoute("anthropic-local", RouteTarget("anthropic", "upstream-message")),
                "responses-local": ModelRoute("responses-local", RouteTarget("responses", "upstream-response")),
            },
            client_key_hashes=frozenset({client_key_digest(CLIENT_KEY)}),
            default_model="chat-local",
            cost_policy="ZERO_COST_ONLY",
        )

        def upstream(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content) if request.content else {}
            self.calls.append((request.url.path, payload, request.headers))
            if request.url.path.endswith("/messages"):
                return httpx.Response(200, json={
                    "id": "msg_test", "type": "message", "role": "assistant",
                    "model": payload.get("model", "upstream-message"),
                    "content": [{"type": "text", "text": "hello"}],
                    "stop_reason": "end_turn", "usage": {"input_tokens": 1, "output_tokens": 1},
                })
            if request.url.path.endswith("/responses"):
                return httpx.Response(200, json={
                    "id": "resp_test", "object": "response", "status": "completed",
                    "model": payload.get("model", "upstream-response"),
                    "output": [{"type": "message", "id": "msg_out", "status": "completed",
                                "role": "assistant", "content": [{"type": "output_text", "text": "ok", "annotations": []}]}],
                    "output_text": "ok",
                })
            if payload.get("stream"):
                event = {"id": "chatcmpl_test", "object": "chat.completion.chunk",
                         "model": payload.get("model"), "choices": [{"index": 0,
                         "delta": {"content": "ok"}, "finish_reason": None}]}
                body = f"data: {json.dumps(event)}\n\ndata: [DONE]\n\n"
                return httpx.Response(200, headers={"content-type": "text/event-stream"}, content=body)
            return httpx.Response(200, json=_chat_response(
                payload.get("model", "upstream-chat"), tool_call=bool(payload.get("tools"))))

        self.upstream = httpx.AsyncClient(
            transport=httpx.MockTransport(upstream), follow_redirects=False, trust_env=False,
        )
        self.test_client_context = patch("zeaz_provider.main.load_settings", return_value=self.settings)
        self.test_client_context.start()
        self.app_lifespan = app.router.lifespan_context(app)
        await self.app_lifespan.__aenter__()
        app.state.router = ProviderRouter(self.settings, self.upstream, app.state.observability)
        self.client = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://provider.test",
        )

    async def asyncTearDown(self):
        await self.client.aclose()
        await self.upstream.aclose()
        await self.app_lifespan.__aexit__(None, None, None)
        self.test_client_context.stop()

    def headers(self):
        return {"Authorization": f"Bearer {CLIENT_KEY}"}

    async def test_models_and_authentication_contract(self):
        denied = await self.client.get("/v1/models")
        self.assertEqual(denied.status_code, 401)
        self.assertEqual(self.calls, [])

        response = await self.client.get("/v1/models", headers=self.headers())
        self.assertEqual(response.status_code, 200)
        self.assertEqual({item["id"] for item in response.json()["data"]}, {
            "chat-local", "anthropic-local", "responses-local",
        })
        self.assertEqual(self.calls, [])

    async def test_chat_completion_forwards_tool_calls_and_rewrites_model_alias(self):
        response = await self.client.post("/v1/chat/completions", headers=self.headers(), json={
            "model": "chat-local",
            "messages": [{"role": "user", "content": "use the tool"}],
            "tools": [{"type": "function", "function": {"name": "lookup", "parameters": {"type": "object"}}}],
        })
        self.assertEqual(response.status_code, 200, response.text)
        value = response.json()
        self.assertEqual(value["model"], "chat-local")
        self.assertEqual(value["choices"][0]["finish_reason"], "tool_calls")
        self.assertEqual(value["choices"][0]["message"]["tool_calls"][0]["function"]["name"], "lookup")
        path, payload, headers = self.calls[-1]
        self.assertEqual(path, "/v1/chat/completions")
        self.assertEqual(payload["model"], "upstream-chat")
        self.assertIn("tools", payload)
        self.assertEqual(headers["authorization"], "Bearer upstream-openai-test-key")

    async def test_anthropic_messages_contract(self):
        response = await self.client.post("/v1/messages", headers=self.headers(), json={
            "model": "anthropic-local", "max_tokens": 32,
            "messages": [{"role": "user", "content": "hello"}],
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["model"], "anthropic-local")
        self.assertEqual(response.json()["content"][0]["text"], "hello")
        path, payload, headers = self.calls[-1]
        self.assertEqual(path, "/v1/messages")
        self.assertEqual(payload["model"], "upstream-message")
        self.assertEqual(headers["x-api-key"], "upstream-anthropic-test-key")

    async def test_responses_endpoint_and_chat_compatibility_conversion(self):
        native = await self.client.post("/v1/responses", headers=self.headers(), json={
            "model": "responses-local", "input": "hello",
        })
        self.assertEqual(native.status_code, 200, native.text)
        self.assertEqual(native.json()["model"], "responses-local")
        self.assertEqual(native.json()["output_text"], "ok")
        self.assertTrue(self.calls[-1][0].endswith("/responses"))
        self.assertEqual(self.calls[-1][1]["model"], "upstream-response")

        converted = await self.client.post("/v1/responses", headers=self.headers(), json={
            "model": "chat-local", "input": "hello",
        })
        self.assertEqual(converted.status_code, 200, converted.text)
        self.assertEqual(converted.json()["model"], "chat-local")
        path, payload, _ = self.calls[-1]
        self.assertEqual(path, "/v1/chat/completions")
        self.assertEqual(payload["messages"], [{"role": "user", "content": "hello"}])

    async def test_chat_stream_emits_openai_sse_with_public_model_name(self):
        response = await self.client.post("/v1/chat/completions", headers=self.headers(), json={
            "model": "chat-local", "stream": True,
            "messages": [{"role": "user", "content": "hello"}],
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        self.assertIn('"model":"chat-local"', response.text)
        self.assertIn("data: [DONE]", response.text)

    async def test_invalid_json_and_model_inputs_fail_before_upstream(self):
        invalid_json = await self.client.post(
            "/v1/chat/completions", headers={**self.headers(), "Content-Type": "application/json"},
            content="{invalid",
        )
        self.assertEqual(invalid_json.status_code, 400)
        invalid_model = await self.client.post("/v1/chat/completions", headers=self.headers(), json={
            "model": "bad\nmodel", "messages": [],
        })
        self.assertEqual(invalid_model.status_code, 400)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
