from __future__ import annotations

from collections.abc import AsyncGenerator

import httpx

from ..exceptions import OllamaConnectionError
from ..models import OllamaModel


class OllamaManager:
    """Async wrapper around the Ollama REST API for model management."""

    def __init__(self, base_url: str = "http://localhost:11434"):
        self._base_url = base_url.rstrip("/")

    async def list_models(self) -> list[OllamaModel]:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self._base_url}/api/tags", timeout=10)
                resp.raise_for_status()
        except httpx.HTTPError as e:
            raise OllamaConnectionError(
                f"Cannot reach Ollama at {self._base_url}: {e}"
            ) from e

        models = []
        for m in resp.json().get("models", []):
            details = m.get("details", {})
            models.append(
                OllamaModel(
                    name=m.get("name", ""),
                    size=m.get("size", 0),
                    parameter_size=details.get("parameter_size", ""),
                    quantization=details.get("quantization_level", ""),
                    modified_at=m.get("modified_at", ""),
                    family=details.get("family", ""),
                )
            )
        models.sort(key=lambda m: m.name)
        return models

    async def show_model(self, name: str) -> dict:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._base_url}/api/show",
                    json={"model": name},
                    timeout=10,
                )
                resp.raise_for_status()
        except httpx.HTTPError as e:
            raise OllamaConnectionError(f"Cannot get model info: {e}") from e
        return resp.json()

    async def pull_model(self, name: str) -> AsyncGenerator[dict, None]:
        try:
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/api/pull",
                    json={"model": name, "stream": True},
                    timeout=httpx.Timeout(10, read=600),
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line:
                            continue
                        import json

                        yield json.loads(line)
        except httpx.HTTPError as e:
            raise OllamaConnectionError(f"Failed to pull model: {e}") from e

    async def delete_model(self, name: str) -> None:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.request(
                    "DELETE",
                    f"{self._base_url}/api/delete",
                    json={"model": name},
                    timeout=30,
                )
                resp.raise_for_status()
        except httpx.HTTPError as e:
            raise OllamaConnectionError(f"Failed to delete model: {e}") from e
