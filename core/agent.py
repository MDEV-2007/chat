"""Agent loop: single streaming call per turn; tool calls arrive in the final chunk.

Some models occasionally emit a malformed pseudo-XML tool call as plain content
(e.g. `<function=search_web> <parameter=query> ... </parameter> </function>`)
instead of a proper tool_calls response — and once that text lands in the
conversation history, the model tends to imitate it on later turns too. We
detect that pattern mid-stream, suppress it from the UI, parse it as a real
tool call, and never persist the broken text back into history.
"""
import json
import re
from typing import AsyncIterator, Callable, Optional

from core.ollama_client import stream_chat
from tools.registry import TOOL_SCHEMAS, execute_tool

MAX_TOOL_ITERATIONS = 5

PSEUDO_TAG_MARKERS = ("<function=", "<tool_call>")
FUNC_RE = re.compile(r"<function=([\w\-]+)>(.*?)(?:</function>|$)", re.S)
PARAM_RE = re.compile(r"<parameter=([\w\-]+)>\s*(.*?)\s*</parameter>", re.S)


def _parse_pseudo_tool_call(text: str) -> Optional[dict]:
    m = FUNC_RE.search(text)
    if not m:
        return None
    name = m.group(1)
    args = {pm.group(1): pm.group(2).strip() for pm in PARAM_RE.finditer(m.group(2))}
    return {"function": {"name": name, "arguments": args}}


async def run_agent_turn(
    model: str,
    messages: list[dict],
    on_tool_call: Optional[Callable[[str, dict], None]] = None,
    on_tool_result: Optional[Callable[[str, dict], None]] = None,
    stats: Optional[dict] = None,
) -> AsyncIterator[str]:
    working = [dict(m) for m in messages]

    for _ in range(MAX_TOOL_ITERATIONS):
        tool_calls = None
        turn_content = ""
        turn_done = {}
        flushed = 0
        pseudo_tag_at = None

        async for chunk in stream_chat(model, working, tools=TOOL_SCHEMAS):
            if chunk["type"] == "content":
                turn_content += chunk["delta"]
                if pseudo_tag_at is None:
                    for marker in PSEUDO_TAG_MARKERS:
                        idx = turn_content.find(marker)
                        if idx != -1:
                            pseudo_tag_at = idx
                            break
                if pseudo_tag_at is None:
                    new_text = turn_content[flushed:]
                    if new_text:
                        yield new_text
                        flushed = len(turn_content)
                # else: a pseudo tool-call tag is forming — stop streaming it to the UI
            else:
                tool_calls = chunk["tool_calls"]
                turn_done = chunk

        clean_content = turn_content

        if not tool_calls:
            parsed = _parse_pseudo_tool_call(turn_content)
            if parsed:
                tool_calls = [parsed]
                clean_content = turn_content[:pseudo_tag_at].strip() if pseudo_tag_at is not None else ""
            else:
                if stats is not None:
                    stats.update(turn_done)
                if flushed < len(turn_content):
                    yield turn_content[flushed:]
                return

        working.append({"role": "assistant", "content": clean_content, "tool_calls": tool_calls})

        for call in tool_calls:
            fn = call.get("function", {})
            name = fn.get("name", "")
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except ValueError:
                    args = {}

            if on_tool_call:
                on_tool_call(name, args)

            result = await execute_tool(name, args)

            if on_tool_result:
                on_tool_result(name, result)

            working.append(
                {"role": "tool", "content": json.dumps(result, ensure_ascii=False), "name": name}
            )

    yield "\n\n_Tool call limit reached._"
