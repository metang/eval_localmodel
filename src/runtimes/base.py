"""Abstract base class for all local-model runtimes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from src.models import ToolCallResult


@dataclass
class RuntimeConfig:
    """Configuration for a runtime backend."""

    name: str
    base_url: str = ""
    api_key: str = "not-needed"
    model_id: str = ""
    extra: dict = field(default_factory=dict)


class BaseRuntime(ABC):
    """Every runtime must implement this interface."""

    def __init__(self, config: RuntimeConfig):
        self.config = config

    # -- required ----------------------------------------------------------

    @abstractmethod
    def chat_with_tools(
        self,
        messages: list[dict],
        tools: list[dict],
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> ToolCallResult:
        """Send a chat-completion request that includes tool definitions."""
        ...

    @abstractmethod
    def list_models(self) -> list[str]:
        """Return model IDs available on this runtime."""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the runtime is reachable and ready."""
        ...

    # -- optional overrides ------------------------------------------------

    def warmup(self) -> None:
        """Pre-load the model so the first real call isn't a cold start."""
        pass

    def cleanup(self) -> None:
        """Release resources (GPU memory, server handles, …)."""
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(model={self.config.model_id!r})"
