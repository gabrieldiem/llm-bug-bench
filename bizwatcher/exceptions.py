"""Domain exceptions for the bizantine-watcher application."""

from __future__ import annotations


class BizWatcherError(Exception):
    """Base exception for all bizantine-watcher errors."""


class TestNotFoundError(BizWatcherError):
    """Raised when a test case ID cannot be found."""


class RunNotFoundError(BizWatcherError):
    """Raised when a run directory cannot be found."""


class ProviderError(BizWatcherError):
    """Raised for LLM provider configuration errors."""


class OllamaConnectionError(ProviderError):
    """Raised when the Ollama API is unreachable."""


class JudgeParseError(BizWatcherError):
    """Raised when the judge response cannot be parsed as JSON."""


class DuplicateTestIdError(BizWatcherError):
    """Raised when creating a test case with an ID that already exists."""
