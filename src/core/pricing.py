"""Token-based cost estimation for OpenAI and Gemini providers."""

from __future__ import annotations

# {model_name_prefix: (input_usd_per_1m, output_usd_per_1m)}
# Prices sourced from official provider pages (2026-03).
# Uses longest-prefix matching, so more specific prefixes must be listed
# alongside shorter ones — the lookup always picks the longest match.
_PRICES: dict[str, tuple[float, float]] = {
    # --- OpenAI ---
    # GPT-5 family
    "gpt-5-nano": (0.05, 0.40),
    "gpt-5-mini": (0.25, 2.00),
    "gpt-5.3-chat-latest": (1.75, 14.00),
    "gpt-5.2-chat-latest": (1.75, 14.00),
    "gpt-5.1-chat-latest": (1.25, 10.00),
    "gpt-5-chat-latest": (1.25, 10.00),
    "gpt-5": (1.25, 10.00),
    # GPT-4.1 family
    "gpt-4.1-nano": (0.10, 0.40),
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4.1": (2.00, 8.00),
    # GPT-4o family
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.00),
    # Legacy GPT-4
    "gpt-4-turbo": (5.00, 15.00),
    "gpt-4": (30.00, 60.00),
    # Legacy GPT-3.5
    "gpt-3.5-turbo": (0.50, 1.50),
    # o-series (longer prefixes first so they win over "o3"/"o1")
    "o4-mini": (1.10, 4.40),
    "o3-mini": (1.10, 4.40),
    "o3-pro": (20.00, 80.00),
    "o3": (2.00, 8.00),
    "o1-mini": (0.55, 2.20),
    "o1-pro": (150.00, 600.00),
    "o1": (15.00, 60.00),
    # Codex
    "codex-mini": (0.75, 3.00),
    # --- Google Gemini ---
    # Gemini 3.x previews
    "gemini-3.1-pro-preview": (2.00, 12.00),
    "gemini-3.1-flash-lite-preview": (0.25, 1.50),
    "gemini-3-flash-preview": (0.50, 3.00),
    # Gemini 2.5 family
    "gemini-2.5-flash-lite": (0.10, 0.40),
    "gemini-2.5-flash": (0.30, 2.50),
    "gemini-2.5-pro": (1.25, 10.00),
    # Gemini 2.0 family
    "gemini-2.0-flash-lite": (0.075, 0.30),
    "gemini-2.0-flash": (0.10, 0.40),
    # Gemini 1.5 family (legacy)
    "gemini-1.5-pro": (1.25, 5.00),
    "gemini-1.5-flash": (0.075, 0.30),
}


def estimate_cost(
    provider: str,
    model: str,
    prompt_tokens: int | None,
    completion_tokens: int | None,
) -> float | None:
    """Return estimated USD cost, 0.0 for Ollama, None if pricing unknown."""
    if provider in ("ollama", "llamacpp"):
        return 0.0
    if prompt_tokens is None and completion_tokens is None:
        return None
    prices = _lookup_price(model)
    if prices is None:
        return None
    input_price, output_price = prices
    cost = (
        (prompt_tokens or 0) * input_price + (completion_tokens or 0) * output_price
    ) / 1_000_000
    return round(cost, 6)


def _lookup_price(model: str) -> tuple[float, float] | None:
    """Longest-prefix match against pricing table."""
    model_lower = model.lower()
    match = None
    for key in _PRICES:
        if model_lower.startswith(key) and (match is None or len(key) > len(match)):
            match = key
    return _PRICES[match] if match else None
