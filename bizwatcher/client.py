from __future__ import annotations

import time

import openai


class LLMClient:
    def __init__(self, api_url: str, model: str, temperature: float, max_tokens: int):
        self.client = openai.OpenAI(base_url=api_url, api_key="not-needed")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def query(self, system_prompt: str, user_prompt: str) -> tuple[str, object, float]:
        """Returns (response_text, usage_object, elapsed_seconds)."""
        start = time.monotonic()
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        elapsed = time.monotonic() - start
        text = response.choices[0].message.content or ""
        return text, response.usage, elapsed
