"""Core data models shared across the framework."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MatchLevel(Enum):
    """How strictly to compare expected vs actual arguments."""

    EXACT = "exact"
    FUZZY = "fuzzy"
    TYPE_ONLY = "type_only"


@dataclass
class ToolCallResult:
    """Parsed result from a runtime's chat-with-tools call."""

    tool_calls: list[dict] = field(default_factory=list)
    # Each entry: {"name": str, "arguments": dict}
    content: str | None = None
    raw_response: Any = None
    usage: dict = field(default_factory=dict)
    # {"prompt_tokens": int, "completion_tokens": int}
    timing: dict = field(default_factory=dict)
    # {"total_ms": float, "ttft_ms": float | None, ...}


@dataclass
class TestCase:
    """A single evaluation test case."""

    id: str
    category: str
    description: str
    messages: list[dict]
    tools: list[dict]
    expected_tool_calls: list[dict] = field(default_factory=list)
    # [{"name": "fn_name", "arguments": {"key": "value"}}]
    match_level: MatchLevel = MatchLevel.FUZZY
    is_negative: bool = False  # True → model should NOT call any tool
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> TestCase:
        match_raw = data.get("match_level", "fuzzy")
        return cls(
            id=data["id"],
            category=data.get("category", "uncategorized"),
            description=data.get("description", ""),
            messages=data["messages"],
            tools=data["tools"],
            expected_tool_calls=data.get("expected_tool_calls", []),
            match_level=MatchLevel(match_raw),
            is_negative=data.get("is_negative", False),
            tags=data.get("tags", []),
        )


@dataclass
class EvalResult:
    """Result of evaluating one test case on one runtime/model."""

    test_id: str
    category: str
    runtime_name: str
    model_id: str
    tool_name_correct: bool = False
    argument_scores: dict[str, bool] = field(default_factory=dict)
    full_match: bool = False
    hallucinated_tools: bool = False
    hallucinated_args: list[str] = field(default_factory=list)
    expected_negative: bool = False  # should have been no-call
    correctly_refused: bool = False  # did it actually refuse?
    latency_ms: float = 0.0
    tokens_per_sec: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw_response: Any = None
    error: str | None = None

    @property
    def argument_accuracy(self) -> float:
        if not self.argument_scores:
            return 1.0 if self.tool_name_correct else 0.0
        return sum(self.argument_scores.values()) / len(self.argument_scores)
