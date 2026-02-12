"""Ollama runtime — talks to a running ``ollama serve`` instance."""

from __future__ import annotations

import time
from typing import Any

from openai import OpenAI

from src.models import ToolCallResult
from src.runtimes.base import BaseRuntime, RuntimeConfig
from src.runtimes.parsing import parse_openai_tool_calls
from src.runtimes.registry import register_runtime


@register_runtime("ollama")
class OllamaRuntime(BaseRuntime):
    """OpenAI-compatible client pointed at Ollama's /v1 endpoint."""

    DEFAULT_BASE_URL = "http://localhost:11434/v1"

    def __init__(
        self,
        config: RuntimeConfig | None = None,
        **kwargs: Any,
    ):
        if config is None:
            config = RuntimeConfig(
                name="ollama",
                base_url=self.DEFAULT_BASE_URL,
                api_key="ollama",
                model_id=kwargs.get("model_id", ""),
            )
        if not config.base_url:
            config.base_url = self.DEFAULT_BASE_URL
        if config.api_key == "not-needed":
            config.api_key = "ollama"
        super().__init__(config)
        self._client = OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
        )

    # ---- BaseRuntime interface -------------------------------------------

    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> ToolCallResult:
        start = time.perf_counter()
        response = self._client.chat.completions.create(
            model=self.config.model_id,
            messages=messages,
            tools=tools if tools else None,
            temperature=temperature,
            **kwargs,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        msg = response.choices[0].message
        parsed_calls = parse_openai_tool_calls(msg)

        usage = {}
        if response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
            }

        tps = 0.0
        if usage.get("completion_tokens") and elapsed_ms > 0:
            tps = usage["completion_tokens"] / (elapsed_ms / 1000)

        return ToolCallResult(
            tool_calls=parsed_calls,
            content=msg.content,
            raw_response=response,
            usage=usage,
            timing={"total_ms": elapsed_ms, "tokens_per_sec": tps},
        )

    def list_models(self) -> list[str]:
        return [m.id for m in self._client.models.list()]

    def health_check(self) -> bool:
        try:
            self._client.models.list()
            return True
        except Exception:
            return False

    def warmup(self) -> None:
        """Send a tiny request to force-load the model into memory."""
        try:
            self._client.chat.completions.create(
                model=self.config.model_id,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
        except Exception:
            pass

