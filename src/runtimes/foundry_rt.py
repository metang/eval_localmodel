"""Foundry Local runtime — ONNX Runtime GenAI via OpenAI-compatible API."""

from __future__ import annotations

import time
from typing import Any

from openai import OpenAI

from src.models import ToolCallResult
from src.runtimes.base import BaseRuntime, RuntimeConfig
from src.runtimes.parsing import parse_openai_tool_calls
from src.runtimes.registry import register_runtime


@register_runtime("foundry-local")
class FoundryLocalRuntime(BaseRuntime):
    """Connects to Foundry Local's OpenAI-compatible endpoint.

    Usage options:

    1.  **With foundry-local-sdk** (auto-starts the service)::

            runtime = FoundryLocalRuntime(alias="phi-4-mini")

    2.  **Manual endpoint** (you start ``foundry model run`` yourself)::

            cfg = RuntimeConfig(name="foundry-local",
                                base_url="http://localhost:5273/v1",
                                model_id="phi-4-mini-onnx")
            runtime = FoundryLocalRuntime(config=cfg)
    """

    def __init__(
        self,
        config: RuntimeConfig | None = None,
        *,
        alias: str | None = None,
        device: str | None = None,
        **kwargs: Any,
    ):
        self._manager = None

        if alias and config is None:
            # Auto-start via SDK
            try:
                from foundry_local import FoundryLocalManager
                from foundry_local.models import DeviceType

                device_type = None
                if device:
                    device_type = DeviceType(device.upper())

                self._manager = FoundryLocalManager(
                    alias, device=device_type,
                )
                # Unload all models to ensure clean isolation
                self._unload_all()
                # Load the requested model and use its actual ID
                model_info = self._manager.load_model(alias, device=device_type)
                config = RuntimeConfig(
                    name="foundry-local",
                    base_url=self._manager.endpoint,
                    api_key=self._manager.api_key,
                    model_id=model_info.id,
                )
            except ImportError:
                raise ImportError(
                    "Install foundry-local-sdk to use auto-start: "
                    "pip install foundry-local-sdk"
                )
        elif config is None:
            raise ValueError("Provide either a RuntimeConfig or an alias")

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
        try:
            self._client.chat.completions.create(
                model=self.config.model_id,
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=1,
            )
        except Exception:
            pass

    def cleanup(self) -> None:
        """Unload all models to free resources."""
        self._unload_all()

    def _unload_all(self) -> None:
        """Unload every loaded model from the Foundry Local service."""
        if not self._manager:
            return
        try:
            for model in self._manager.list_loaded_models():
                self._manager.unload_model(model.id)
        except Exception:
            pass

