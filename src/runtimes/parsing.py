"""Shared helpers for parsing tool-call responses from OpenAI-compatible APIs."""

from __future__ import annotations

import json
from typing import Any


def parse_openai_tool_calls(msg: Any) -> list[dict]:
    """Extract tool calls from an OpenAI-style message *object* (attribute access).

    Works with responses from the ``openai`` Python client where tool calls
    are accessed as ``msg.tool_calls[i].function.name``.
    """
    if not msg.tool_calls:
        return []
    calls: list[dict] = []
    for tc in msg.tool_calls:
        try:
            args = json.loads(tc.function.arguments)
        except (json.JSONDecodeError, TypeError):
            args = tc.function.arguments
        calls.append({"name": tc.function.name, "arguments": args})
    return calls


def parse_dict_tool_calls(msg: dict) -> list[dict]:
    """Extract tool calls from a plain-dict response (e.g. llama-cpp in-process).

    Expects ``msg["tool_calls"][i]["function"]["name" / "arguments"]``.
    """
    raw = msg.get("tool_calls") or []
    calls: list[dict] = []
    for tc in raw:
        fn = tc.get("function", {})
        raw_args = fn.get("arguments", {})
        if isinstance(raw_args, str):
            try:
                raw_args = json.loads(raw_args)
            except json.JSONDecodeError:
                pass
        calls.append({"name": fn.get("name", ""), "arguments": raw_args})
    return calls


def estimate_tokens(text: str | None) -> int:
    """Estimate token count from text using a simple heuristic.

    Uses ~4 characters per token as a rough approximation (common for English).
    This is a fallback when the API doesn't provide usage.completion_tokens.
    """
    if not text:
        return 0
    # Simple heuristic: ~4 chars per token for English text
    return max(1, len(text) // 4)


def estimate_completion_tokens(msg: Any, parsed_calls: list[dict]) -> int:
    """Estimate completion tokens from message content and tool calls.

    Combines text content length with serialized tool call arguments.
    """
    total_text = ""

    # Add message content
    if hasattr(msg, "content") and msg.content:
        total_text += msg.content

    # Add tool call function names and arguments
    for call in parsed_calls:
        total_text += call.get("name", "")
        args = call.get("arguments", {})
        if isinstance(args, dict):
            total_text += json.dumps(args)
        elif isinstance(args, str):
            total_text += args

    return estimate_tokens(total_text)
