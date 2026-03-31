import json
import logging
import re
import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any, cast

import httpx
from mcp.types import TextContent

from prompts import PromptLoader

from .. import settings
from ..schemas import ChatRequest
from ..services import mcp_manager

logger = logging.getLogger("gateway.chat")

TOOL_CALL_RE = re.compile(
    r"\[TOOL_CALLS\]\s*(?P<name>[^\[\]]+?)\s*\[ARGS\]\s*(?P<args>\{.*?\})", re.DOTALL
)
_TRIGGERS = ["[TOOL_CALLS]", "<think>", "</think>"]


def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _text_event(content: str) -> str:
    return _sse("text", {"choices": [{"delta": {"content": content}}]})


@dataclass
class _StreamState:
    in_think_block: bool = False
    current_tool_calls: dict[int, dict[str, Any]] = field(
        default_factory=dict[int, dict[str, Any]]
    )
    yielded_call_ids: set[str] = field(default_factory=set[str])
    finish_reason: str | None = None
    partial_text: list[str] = field(default_factory=list[str])
    text_buffer: str = ""


async def format_mcp_tools_for_openai() -> list[dict[str, object]]:
    """Récupère les outils du serveur MCP et les formate pour le LLM."""
    if not mcp_manager.session:
        raise RuntimeError("Session MCP non initialisée")

    tools_response = await mcp_manager.session.list_tools()
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema,
            },
        }
        for tool in tools_response.tools
    ]


def _accumulate_native_tool_call(state: _StreamState, tc: dict[str, Any]) -> str:
    """Merge a streaming tool_call chunk into state and return an SSE event."""
    idx = tc["index"]
    if idx not in state.current_tool_calls:
        state.current_tool_calls[idx] = {
            "id": tc["id"],
            "type": "function",
            "function": {"name": tc["function"]["name"], "arguments": ""},
        }
    if "arguments" in tc["function"]:
        state.current_tool_calls[idx]["function"]["arguments"] += tc["function"][
            "arguments"
        ]
    return _sse("tool_call_start", list(state.current_tool_calls.values()))


def _process_think_in_buffer(state: _StreamState) -> tuple[list[str], bool]:
    """Handle <think>…</think> tags in state.text_buffer.

    Returns (events, should_continue). should_continue=True means skip
    inline tool-call parsing and buffer flushing for this chunk.
    """
    events: list[str] = []

    if not state.in_think_block and "<think>" in state.text_buffer:
        before, _, after = state.text_buffer.partition("<think>")
        if before:
            events.append(_text_event(before))
            state.partial_text.append(before)
        state.text_buffer = "<think>" + after
        state.in_think_block = True

    if not state.in_think_block:
        return events, False

    if "</think>" in state.text_buffer:
        think_part, _, rest = state.text_buffer.partition("</think>")
        think_content = think_part.replace("<think>", "")
        if think_content:
            events.append(_sse("thinking", {"content": think_content}))
        state.text_buffer = rest
        state.in_think_block = False
        return events, False
    else:
        think_content = state.text_buffer.replace("<think>", "")
        if think_content:
            events.append(_sse("thinking", {"content": think_content}))
        state.text_buffer = "<think>"

    return events, True


def _process_inline_tool_calls(state: _StreamState) -> list[str]:
    """Parse and extract [TOOL_CALLS] markers from state.text_buffer."""
    events: list[str] = []

    while "[TOOL_CALLS]" in state.text_buffer:
        m = TOOL_CALL_RE.search(state.text_buffer)
        if m:
            text_before = state.text_buffer[: m.start()]
            if text_before:
                events.append(_text_event(text_before))
                state.partial_text.append(text_before)

            try:
                args_obj = json.loads(m.group("args"))
            except Exception:
                args_obj = None

            next_idx = (
                max(state.current_tool_calls) + 1 if state.current_tool_calls else 0
            )
            call_id = f"adhoc_{uuid.uuid4().hex[:8]}"
            state.current_tool_calls[next_idx] = {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": m.group("name").strip(),
                    "arguments": json.dumps(args_obj) if args_obj is not None else "",
                },
            }

            new_calls = [
                c
                for c in state.current_tool_calls.values()
                if c["id"] not in state.yielded_call_ids
            ]
            if new_calls:
                events.append(_sse("tool_call_start", new_calls))
                state.yielded_call_ids.update(c["id"] for c in new_calls)

            state.text_buffer = state.text_buffer[m.end() :]
        else:
            idx = state.text_buffer.find("[TOOL_CALLS]")
            text_before = state.text_buffer[:idx]
            if text_before:
                events.append(_text_event(text_before))
                state.partial_text.append(text_before)
            state.text_buffer = state.text_buffer[idx:]
            break

    return events


def _flush_safe_buffer(state: _StreamState) -> list[str]:
    """Yield buffer content, holding back any partial trigger suffix."""
    if not state.text_buffer or state.text_buffer.startswith("[TOOL_CALLS]"):
        return []

    partial_match_len = max(
        (
            i
            for trigger in _TRIGGERS
            for i in range(1, len(trigger))
            if state.text_buffer.endswith(trigger[:i])
        ),
        default=0,
    )

    if partial_match_len:
        safe, state.text_buffer = (
            state.text_buffer[:-partial_match_len],
            state.text_buffer[-partial_match_len:],
        )
    else:
        safe, state.text_buffer = state.text_buffer, ""

    if safe:
        state.partial_text.append(safe)
        return [_text_event(safe)]
    return []


def _process_content_chunk(content: str, state: _StreamState) -> list[str]:
    """Accumulate content into the buffer and dispatch to tag/tool parsers."""
    state.text_buffer += content

    think_events, should_continue = _process_think_in_buffer(state)
    if should_continue:
        return think_events

    return think_events + _process_inline_tool_calls(state) + _flush_safe_buffer(state)


def _drain_buffer(state: _StreamState) -> list[str]:
    """Flush whatever remains in the buffer after the stream ends."""
    events = _process_inline_tool_calls(state)
    if state.text_buffer and not state.text_buffer.startswith("[TOOL_CALLS]"):
        content, state.text_buffer = state.text_buffer, ""
        state.partial_text.append(content)
        events.append(_text_event(content))
    return events


def _prepare_messages(request: ChatRequest) -> list[dict[str, Any]]:
    messages = [m.model_dump(exclude_none=True) for m in request.messages]
    try:
        system_prompt = PromptLoader.get("system", "expert", "content")
        messages.insert(0, {"role": "system", "content": system_prompt})
    except KeyError as e:
        logger.warning("Prompt système 'system.expert.content' introuvable : %s", e)
    return messages


def _append_assistant_turn(messages: list[dict[str, Any]], state: _StreamState) -> None:
    """Append the assistant turn (text + optional tool_calls) to the conversation."""
    tool_calls = (
        list(state.current_tool_calls.values()) if state.current_tool_calls else None
    )

    if state.partial_text:
        msg: dict[str, Any] = {
            "role": "assistant",
            "content": "".join(state.partial_text),
        }
        if tool_calls:
            msg["tool_calls"] = tool_calls
        messages.append(msg)
    elif tool_calls:
        messages.append(
            {"role": "assistant", "content": None, "tool_calls": tool_calls}
        )


async def _call_mcp_tool(tool_name: str, tool_args: dict[str, Any] | None) -> str:
    if not mcp_manager.session:
        raise RuntimeError("Session MCP non initialisée")

    if isinstance(tool_args, dict) and isinstance(tool_args.get("query"), list):
        tool_args["query"] = " ".join(str(x) for x in tool_args["query"])

    mcp_result = await mcp_manager.session.call_tool(tool_name, tool_args)
    first = mcp_result.content[0]
    return (
        first.text
        if isinstance(first, TextContent)
        else json.dumps(mcp_result.model_dump())
    )


async def _execute_tool_calls(
    tool_calls: list[dict[str, Any]], messages: list[dict[str, Any]]
) -> AsyncGenerator[str, None]:
    for tc in tool_calls:
        tool_name: str = tc["function"]["name"]
        try:
            raw = (
                json.loads(tc["function"]["arguments"])
                if tc["function"].get("arguments")
                else None
            )
            tool_args: dict[str, Any] | None = (
                cast(dict[str, Any], raw) if raw is not None else None
            )
        except Exception:
            tool_args = {}

        try:
            result_str = await _call_mcp_tool(tool_name, tool_args)
        except Exception as e:
            result_str = json.dumps({"error": str(e)})

        yield _sse("tool_result", {"id": tc["id"], "result": result_str})
        messages.append(
            {"role": "tool", "tool_call_id": tc["id"], "content": result_str}
        )


async def stream_chat_loop(request: ChatRequest) -> AsyncGenerator[str, None]:
    """Exécute la boucle de chat avec gestion des outils MCP et du thinking."""
    headers = (
        {"Authorization": f"Bearer {settings.llm_api_key}"}
        if settings.llm_api_key
        else {}
    )
    messages = _prepare_messages(request)
    tools = await format_mcp_tools_for_openai()

    async with httpx.AsyncClient(timeout=120.0) as client:
        for _ in range(settings.max_tool_iterations):
            payload: dict[str, object] = {
                "model": request.model or settings.llm_model,
                "messages": messages,
                "stream": True,
                "temperature": request.temperature or settings.llm_temperature,
                "tools": tools,
            }

            state = _StreamState()

            async with client.stream(
                "POST",
                f"{settings.llm_base_url}/chat/completions",
                json=payload,
                headers=headers,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue
                    try:
                        chunk = json.loads(line.removeprefix("data: "))
                    except json.JSONDecodeError:
                        continue

                    choice = chunk["choices"][0]
                    delta = choice.get("delta", {})
                    state.finish_reason = choice.get("finish_reason")

                    if tool_calls_chunk := delta.get("tool_calls"):
                        for tc in tool_calls_chunk:
                            yield _accumulate_native_tool_call(state, tc)
                        continue

                    if thinking := delta.get("reasoning_content") or delta.get(
                        "thinking"
                    ):
                        yield _sse("thinking", {"content": thinking})
                        continue

                    if content := delta.get("content"):
                        for event in _process_content_chunk(content, state):
                            yield event

            for event in _drain_buffer(state):
                yield event

            _append_assistant_turn(messages, state)

            if state.current_tool_calls:
                async for event in _execute_tool_calls(
                    list(state.current_tool_calls.values()), messages
                ):
                    yield event
                continue

            if state.finish_reason in ("stop", "length"):
                break

    yield "event: text\ndata: [DONE]\n\n"
