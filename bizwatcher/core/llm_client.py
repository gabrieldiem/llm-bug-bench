from __future__ import annotations

import json as _json
import sys
import time
import urllib.request

import openai

from ..exceptions import ProviderError
from ..models import ProviderConfig

GEMINI_OPENAI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"


class LLMClient:
    """OpenAI-compatible LLM client with Ollama native streaming support."""

    def __init__(
        self,
        api_url: str,
        model: str,
        temperature: float,
        max_tokens: int,
        api_key: str = "ollama",
        think: bool = False,
        debug: bool = False,
    ):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.think = think
        self.debug = debug

        base = api_url.rstrip("/")
        if base.endswith("/v1") and api_key == "ollama":
            self._ollama_base: str | None = base[:-3]
        else:
            self._ollama_base = None
            self._openai_client = openai.OpenAI(base_url=api_url, api_key=api_key)

    def query(self, system_prompt: str, user_prompt: str) -> tuple[str, object, float]:
        """Returns (response_text, usage_object, elapsed_seconds)."""
        if not self.think:
            user_prompt = user_prompt + "\n/no_think"
        if self._ollama_base is not None:
            return self._query_ollama_native(system_prompt, user_prompt)
        return self._query_openai(system_prompt, user_prompt)

    def _query_ollama_native(
        self, system_prompt: str, user_prompt: str
    ) -> tuple[str, object, float]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": True,
            "think": self.think,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens,
            },
        }
        url = f"{self._ollama_base}/api/chat"
        req = urllib.request.Request(
            url,
            data=_json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        prompt_tokens = completion_tokens = total_tokens = None
        start = time.monotonic()
        with urllib.request.urlopen(req) as resp:
            for raw_line in resp:
                line = raw_line.strip()
                if not line:
                    continue
                obj = _json.loads(line)
                if self.debug:
                    print(repr(obj), file=sys.stderr)
                msg = obj.get("message", {})
                if msg.get("thinking"):
                    reasoning_parts.append(msg["thinking"])
                if msg.get("content"):
                    content_parts.append(msg["content"])
                if obj.get("done"):
                    prompt_tokens = obj.get("prompt_eval_count")
                    completion_tokens = obj.get("eval_count")
                    total_tokens = (prompt_tokens or 0) + (completion_tokens or 0)
        elapsed = time.monotonic() - start
        text = "".join(content_parts) or "".join(reasoning_parts)

        class _Usage:
            pass

        usage = _Usage()
        usage.prompt_tokens = prompt_tokens  # type: ignore[attr-defined]
        usage.completion_tokens = completion_tokens  # type: ignore[attr-defined]
        usage.total_tokens = total_tokens  # type: ignore[attr-defined]
        return text, usage, elapsed

    def _query_openai(
        self, system_prompt: str, user_prompt: str
    ) -> tuple[str, object, float]:
        start = time.monotonic()
        stream = self._openai_client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
            stream_options={"include_usage": True},
            extra_body={"think": self.think},
        )
        content_parts: list[str] = []
        reasoning_parts: list[str] = []
        usage = None
        for chunk in stream:
            if self.debug:
                print(repr(chunk), file=sys.stderr)
            if chunk.choices:
                delta = chunk.choices[0].delta
                if delta.content:
                    content_parts.append(delta.content)
                rc = (delta.model_extra or {}).get("thinking")
                if rc:
                    reasoning_parts.append(rc)
            if chunk.usage:
                usage = chunk.usage
        elapsed = time.monotonic() - start
        text = "".join(content_parts) or "".join(reasoning_parts)
        return text, usage, elapsed


def create_client_from_config(config: ProviderConfig, **kwargs) -> LLMClient:
    """Factory: build an LLMClient from a ProviderConfig."""
    if config.provider == "ollama":
        return LLMClient(
            api_url=config.api_url,
            model=config.model,
            api_key="ollama",
            **kwargs,
        )
    if config.provider == "openai":
        return LLMClient(
            api_url="https://api.openai.com/v1",
            model=config.model,
            api_key=config.api_key,
            **kwargs,
        )
    if config.provider == "gemini":
        return LLMClient(
            api_url=GEMINI_OPENAI_BASE_URL,
            model=config.model,
            api_key=config.api_key,
            **kwargs,
        )
    raise ProviderError(f"Unknown provider: {config.provider}")
