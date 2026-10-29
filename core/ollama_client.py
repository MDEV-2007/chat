"""Async Ollama REST client: model list + streaming chat."""
import json
from typing import AsyncIterator, Optional

import httpx

from core.config import OLLAMA_HOST


async def list_models() -> list[str]:
    """Returns chat-capable model names (excludes embedding-only models)."""
    info = await list_models_info()
    return list(info.keys())


async def list_models_info() -> dict[str, list[str]]:
    """Returns {model_name: capabilities} for chat-capable models."""
    async with httpx.AsyncClient(base_url=OLLAMA_HOST, timeout=10) as client:
        resp = await client.get("/api/tags")
        resp.raise_for_status()
        data = resp.json()
        info = {}
        for m in data.get("models", []):
            caps = m.get("capabilities") or []
            if caps and "completion" not in caps:
                continue
            info[m["name"]] = caps
        return info


async def stream_chat(
    model: str,
    messages: list[dict],
    images_b64: Optional[list[str]] = None,
    tools: Optional[list[dict]] = None,
) -> AsyncIterator[dict]:
    """Streams /api/chat. Yields {'type':'content','delta':str} and a final
    {'type':'done','tool_calls':list|None}. think=False for speed (skip qwen3 reasoning)."""
    payload_messages = [dict(m) for m in messages]
    if images_b64 and payload_messages:
        payload_messages[-1]["images"] = images_b64

    payload = {
        "model": model,
        "messages": payload_messages,
        "stream": True,
        "think": False,
    }
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(base_url=OLLAMA_HOST, timeout=None) as client:
        async with client.stream("POST", "/api/chat", json=payload) as resp:
            resp.raise_for_status()
            collected_tool_calls = None
            async for line in resp.aiter_lines():
                if not line.strip():
                    continue
                chunk = json.loads(line)
                msg = chunk.get("message", {})
                delta = msg.get("content", "")
                if delta:
                    yield {"type": "content", "delta": delta}
                if msg.get("tool_calls"):
                    collected_tool_calls = msg["tool_calls"]
                if chunk.get("done"):
                    yield {
                        "type": "done",
                        "tool_calls": collected_tool_calls,
                        "eval_count": chunk.get("eval_count"),
                        "eval_duration": chunk.get("eval_duration"),
                        "total_duration": chunk.get("total_duration"),
                    }
                    break


async def stream_chat_text(
    model: str,
    messages: list[dict],
    images_b64: Optional[list[str]] = None,
    stats: Optional[dict] = None,
) -> AsyncIterator[str]:
    """Simple text-only streaming wrapper (no tools). If `stats` dict is passed,
    it's filled with eval_count/eval_duration/total_duration once the stream ends."""
    async for chunk in stream_chat(model, messages, images_b64=images_b64):
        if chunk["type"] == "content":
            yield chunk["delta"]
        elif stats is not None:
            stats.update(chunk)
