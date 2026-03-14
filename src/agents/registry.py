"""
Agent registry — maps agent names to their classes.

Usage:
    @register
    class MyAgent(BaseAgent):
        name = "my-agent"
        ...

    agent_cls = get_agent("my-agent")
    available = list_agents()
"""

from __future__ import annotations

from typing import Type

from .base import BaseAgent

_REGISTRY: dict[str, Type[BaseAgent]] = {}


def register(cls: Type[BaseAgent]) -> Type[BaseAgent]:
    """Class decorator — registers an agent class under its `name` attribute."""
    if not hasattr(cls, "name") or cls.name == "base-agent":
        raise ValueError(
            f"Agent class {cls.__name__} must define a unique `name` class attribute."
        )
    _REGISTRY[cls.name] = cls
    return cls


def get_agent(name: str) -> Type[BaseAgent] | None:
    """Return the agent class for `name`, or None if not registered."""
    return _REGISTRY.get(name)


def list_agents() -> list[str]:
    """Return names of all registered agents."""
    return sorted(_REGISTRY.keys())
