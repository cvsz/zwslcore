from __future__ import annotations

import time
from typing import Any


class StructuredOutputError(ValueError):
    pass


def structured_schema(payload: dict[str, Any]) -> dict[str, Any] | None:
    response_format = payload.get("response_format")
    if not isinstance(response_format, dict) or response_format.get("type") != "json_schema":
        return None
    json_schema = response_format.get("json_schema")
    if not isinstance(json_schema, dict):
        return None
    schema = json_schema.get("schema")
    return schema if isinstance(schema, dict) else None


def ollama_structured_payload(
    payload: dict[str, Any],
    schema: dict[str, Any],
) -> dict[str, Any]:
    messages = payload.get("messages")
    if not isinstance(messages, list):
        raise StructuredOutputError("structured Ollama request requires messages[]")
    result: dict[str, Any] = {
        "model": payload.get("model"),
        "messages": messages,
        "stream": False,
        "format": schema,
    }
    options: dict[str, Any] = {}
    for source, target in (
        ("temperature", "temperature"),
        ("top_p", "top_p"),
        ("max_tokens", "num_predict"),
    ):
        if source in payload:
            options[target] = payload[source]
    stop = payload.get("stop")
    if stop is not None:
        options["stop"] = stop
    if options:
        result["options"] = options
    return result


def ollama_chat_to_openai(
    payload: dict[str, Any],
    requested_model: str,
) -> dict[str, Any]:
    message = payload.get("message")
    if not isinstance(message, dict):
        raise StructuredOutputError("Ollama returned an invalid structured response")
    content = message.get("content")
    if not isinstance(content, str) or not content.strip():
        raise StructuredOutputError("Ollama returned empty structured content")
    prompt_tokens = payload.get("prompt_eval_count", 0)
    completion_tokens = payload.get("eval_count", 0)
    if type(prompt_tokens) is not int or prompt_tokens < 0:
        prompt_tokens = 0
    if type(completion_tokens) is not int or completion_tokens < 0:
        completion_tokens = 0
    done_reason = payload.get("done_reason")
    finish_reason = "length" if done_reason == "length" else "stop"
    return {
        "id": "chatcmpl_ollama_native",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": requested_model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": finish_reason,
        }],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }
