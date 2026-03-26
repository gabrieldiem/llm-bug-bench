from __future__ import annotations


def compute_tokens_per_second(usage, elapsed_seconds: float) -> float | None:
    if usage and getattr(usage, "completion_tokens", None):
        return usage.completion_tokens / elapsed_seconds
    return None
