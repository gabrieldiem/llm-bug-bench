"""Token throughput calculation from LLM API usage data."""

from __future__ import annotations


def compute_tokens_per_second(usage, elapsed_seconds: float) -> float | None:
    """Compute completion throughput from API usage and wall-clock time.

    Args:
        usage: Object with a ``completion_tokens`` attribute (e.g. OpenAI usage).
        elapsed_seconds: Wall-clock seconds for the request.

    Returns:
        Tokens per second, or None if usage data is unavailable.
    """
    if usage and getattr(usage, "completion_tokens", None):
        return usage.completion_tokens / elapsed_seconds
    return None
