"""Async wrapper around the llama.cpp server REST API for server management."""

from __future__ import annotations

import logging

import httpx

from ..exceptions import LlamaCppConnectionError
from ..models import LlamaCppModelInfo, LlamaCppServerInfo

logger = logging.getLogger(__name__)


def _extract_api_error(exc: httpx.HTTPStatusError) -> str:
    """Extract a human-readable message from an HTTP error response."""
    try:
        body = exc.response.json()
        if "error" in body and isinstance(body["error"], dict):
            return body["error"].get("message", str(exc))
        if "message" in body:
            return body["message"]
    except (ValueError, KeyError):
        pass
    return str(exc)


class LlamaCppManager:
    """Async client for the llama.cpp server management API.

    Supports health checks, server property queries, and slot inspection
    via the llama.cpp REST endpoints at the configured base URL.
    """

    def __init__(self, base_url: str = "http://localhost:8095"):
        self._base_url = base_url.rstrip("/")

    async def health(self) -> str:
        """Check server health status.

        Returns:
            Status string: "ok", "loading model", "error", or "no slot available".

        Raises:
            LlamaCppConnectionError: If the server is unreachable.
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self._base_url}/health", timeout=10)
                data = resp.json()
                return data.get("status", "error")
        except httpx.HTTPStatusError as e:
            msg = _extract_api_error(e)
            raise LlamaCppConnectionError(
                f"Cannot reach llama.cpp server at {self._base_url}: {msg}"
            ) from e
        except httpx.HTTPError as e:
            raise LlamaCppConnectionError(
                f"Cannot reach llama.cpp server at {self._base_url}: {e}"
            ) from e

    async def get_props(self) -> dict:
        """Fetch server properties (model name, context size, etc.).

        Raises:
            LlamaCppConnectionError: If the server is unreachable.
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self._base_url}/props", timeout=10)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            msg = _extract_api_error(e)
            raise LlamaCppConnectionError(
                f"Cannot get server props: {msg}"
            ) from e
        except httpx.HTTPError as e:
            raise LlamaCppConnectionError(
                f"Cannot get server props: {e}"
            ) from e

    async def get_slots(self) -> list[dict]:
        """Fetch active inference slot information.

        Returns empty list when the server returns a 4xx error (e.g. /slots
        requires the --slots flag on some llama.cpp builds).

        Raises:
            LlamaCppConnectionError: If the server is unreachable or returns 5xx.
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self._base_url}/slots", timeout=10)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError as e:
            if 400 <= e.response.status_code < 500:
                msg = _extract_api_error(e)
                logger.warning("/slots returned %d: %s — treating as unavailable", e.response.status_code, msg)
                return []
            msg = _extract_api_error(e)
            raise LlamaCppConnectionError(
                f"Cannot get slot info: {msg}"
            ) from e
        except httpx.HTTPError as e:
            raise LlamaCppConnectionError(
                f"Cannot get slot info: {e}"
            ) from e

    async def list_models(self) -> list[LlamaCppModelInfo]:
        """Fetch models via the OpenAI-compatible /v1/models endpoint.

        Returns:
            List of LlamaCppModelInfo with name and status.

        Raises:
            LlamaCppConnectionError: If the server is unreachable.
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._base_url}/v1/models", timeout=10
                )
                resp.raise_for_status()
                data = resp.json()
                return [
                    LlamaCppModelInfo(
                        name=m["id"],
                        status=m.get("status", {}).get("value", "unknown"),
                    )
                    for m in data.get("data", [])
                ]
        except httpx.HTTPStatusError as e:
            msg = _extract_api_error(e)
            raise LlamaCppConnectionError(
                f"Cannot list models: {msg}"
            ) from e
        except httpx.HTTPError as e:
            raise LlamaCppConnectionError(
                f"Cannot list models: {e}"
            ) from e

    async def unload_model(self, model: str) -> None:
        """Unload a model from VRAM via POST /v1/models/stop.

        Logs a warning on failure instead of raising — eviction is best-effort.
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self._base_url}/v1/models/stop",
                    json={"model": model},
                    timeout=10,
                )
                resp.raise_for_status()
                logger.info("Unloaded llama.cpp model from VRAM: %s", model)
        except httpx.HTTPError as e:
            logger.warning("Failed to unload llama.cpp model %s: %s", model, e)

    async def get_server_info(self) -> LlamaCppServerInfo:
        """Aggregate health, models, and slots into a single server info object.

        Raises:
            LlamaCppConnectionError: If health or models endpoint is unreachable.
        """
        status = await self.health()
        models = await self.list_models()
        slots = await self.get_slots()

        total_slots = len(slots)
        idle_slots = sum(1 for s in slots if s.get("state") == 0)

        return LlamaCppServerInfo(
            server_url=self._base_url,
            health_status=status,
            models=models,
            total_slots=total_slots,
            idle_slots=idle_slots,
        )
