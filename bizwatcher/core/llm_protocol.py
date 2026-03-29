"""Protocol definition for LLM clients, enabling dependency injection."""

from __future__ import annotations

from typing import Any, Protocol


class LLMClientProtocol(Protocol):
    """Structural interface for LLM query clients.

    Any class with a matching ``query`` method satisfies this protocol
    without explicit inheritance.
    """

    def query(self, system_prompt: str, user_prompt: str) -> tuple[str, Any, float]: ...
