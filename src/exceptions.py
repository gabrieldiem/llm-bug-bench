"""Domain exceptions for the llm-bug-bench application."""

from __future__ import annotations


class BenchmarkError(Exception):
    """Base exception for all llm-bug-bench errors."""


class TestNotFoundError(BenchmarkError):
    """Raised when a test case ID cannot be found."""


class RunNotFoundError(BenchmarkError):
    """Raised when a run directory cannot be found."""


class ProviderError(BenchmarkError):
    """Raised for LLM provider configuration errors."""


class OllamaConnectionError(ProviderError):
    """Raised when the Ollama API is unreachable."""


class JudgeParseError(BenchmarkError):
    """Raised when the judge response cannot be parsed as JSON."""


class DuplicateTestIdError(BenchmarkError):
    """Raised when creating a test case with an ID that already exists."""
