from __future__ import annotations

from typing import Any, Protocol


class LLMClientProtocol(Protocol):
    def query(self, system_prompt: str, user_prompt: str) -> tuple[str, Any, float]: ...
