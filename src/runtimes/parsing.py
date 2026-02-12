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
