"""llama-cpp-python runtime — in-process or server mode."""

from __future__ import annotations

import time
from typing import Any

from src.models import ToolCallResult
from src.runtimes.base import BaseRuntime, RuntimeConfig
from src.runtimes.parsing import (
    estimate_completion_tokens,
    parse_dict_tool_calls,
    parse_openai_tool_calls,
)
from src.runtimes.registry import register_runtime


@register_runtime("llama-cpp")
class LlamaCppRuntime(BaseRuntime):
    """Supports two modes:

    * **server** (default) — connects to a ``llama-cpp-python`` OpenAI-
      compatible server at ``base_url``.
    * **in-process** — loads the GGUF file directly via ``llama_cpp.Llama``.
      Pass ``model_path="/path/to.gguf"`` and ``in_process=True``.
    """

    DEFAULT_BASE_URL = "http://localhost:8000/v1"

    def __init__(
        self,
        config: RuntimeConfig | None = None,
        *,
        in_process: bool = False,
        model_path: str | None = None,
        n_ctx: int = 4096,
        n_gpu_layers: int = -1,
        chat_format: str = "chatml-function-calling",
        **kwargs: Any,
    ):
        if config is None:
            config = RuntimeConfig(
                name="llama-cpp",
                base_url=self.DEFAULT_BASE_URL,
                model_id=kwargs.get("model_id", model_path or ""),
            )
        if not config.base_url:
            config.base_url = self.DEFAULT_BASE_URL
        super().__init__(config)

        self._in_process = in_process
        self._llm = None
        self._client = None

        if in_process:
            if not model_path:
                raise ValueError("model_path is required for in-process mode")
            from llama_cpp import Llama

            self._llm = Llama(
                model_path=model_path,
                n_ctx=n_ctx,
                n_gpu_layers=n_gpu_layers,
                chat_format=chat_format,
                verbose=False,
            )
        else:
            from openai import OpenAI

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
        if self._in_process:
            return self._call_in_process(messages, tools, temperature, **kwargs)
        return self._call_server(messages, tools, temperature, **kwargs)

    def list_models(self) -> list[str]:
        if self._in_process:
            return [self.config.model_id]
        assert self._client is not None
        return [m.id for m in self._client.models.list()]

    def health_check(self) -> bool:
        if self._in_process:
            return self._llm is not None
        try:
            assert self._client is not None
            self._client.models.list()
            return True
        except Exception:
            return False

    def cleanup(self) -> None:
        if self._llm is not None:
            del self._llm
            self._llm = None

    # ---- private helpers -------------------------------------------------

    def _call_server(
        self, messages: list[dict], tools: list[dict], temperature: float, **kwargs: Any
    ) -> ToolCallResult:
        assert self._client is not None
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

        # Fallback: estimate tokens if API didn't provide them
        completion_tokens = usage.get("completion_tokens") or 0
        if not completion_tokens:
            completion_tokens = estimate_completion_tokens(msg, parsed_calls)
            usage["completion_tokens"] = completion_tokens
            usage["estimated"] = True

        tps = 0.0
        if completion_tokens and elapsed_ms > 0:
            tps = completion_tokens / (elapsed_ms / 1000)

        return ToolCallResult(
            tool_calls=parsed_calls,
            content=msg.content,
            raw_response=response,
            usage=usage,
            timing={"total_ms": elapsed_ms, "tokens_per_sec": tps},
        )

    def _call_in_process(
        self, messages: list[dict], tools: list[dict], temperature: float, **kwargs: Any
    ) -> ToolCallResult:
        assert self._llm is not None
        start = time.perf_counter()
        result = self._llm.create_chat_completion(
            messages=messages,
            tools=tools if tools else None,
            tool_choice="auto",
            temperature=temperature,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        msg = result["choices"][0]["message"]
        parsed_calls = parse_dict_tool_calls(msg)

        usage = result.get("usage", {})
        if usage:
            usage = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
            }

        # Fallback: estimate tokens if API didn't provide them
        completion_tokens = usage.get("completion_tokens") or 0
        if not completion_tokens:
            # For dict response, wrap msg for estimation
            class MsgWrapper:
                content = msg.get("content")
            completion_tokens = estimate_completion_tokens(MsgWrapper(), parsed_calls)
            usage["completion_tokens"] = completion_tokens
            usage["estimated"] = True

        tps = 0.0
        if completion_tokens and elapsed_ms > 0:
            tps = completion_tokens / (elapsed_ms / 1000)

        return ToolCallResult(
            tool_calls=parsed_calls,
            content=msg.get("content"),
            raw_response=result,
            usage=usage,
            timing={"total_ms": elapsed_ms, "tokens_per_sec": tps},
        )

