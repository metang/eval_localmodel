"""Runtime registry — discover and instantiate backends by name."""

from __future__ import annotations

from typing import Type

from src.runtimes.base import BaseRuntime, RuntimeConfig

_REGISTRY: dict[str, Type[BaseRuntime]] = {}


def register_runtime(name: str):
    """Class decorator that registers a runtime under *name*."""

    def decorator(cls: Type[BaseRuntime]):
        _REGISTRY[name] = cls
        return cls

    return decorator


def create_runtime(name: str, config: RuntimeConfig | None = None, **kwargs) -> BaseRuntime:
    """Instantiate a runtime by its registered name."""
    if name not in _REGISTRY:
        raise ValueError(
            f"Unknown runtime: {name!r}. Available: {sorted(_REGISTRY.keys())}"
        )
    return _REGISTRY[name](config=config, **kwargs)


def list_runtimes() -> list[str]:
    return sorted(_REGISTRY.keys())


# ---------- auto-import concrete implementations -------------------------
# Import them so their @register_runtime decorators fire.
from src.runtimes import ollama_rt, llamacpp_rt, foundry_rt  # noqa: F401, E402
