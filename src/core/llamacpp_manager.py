"""Async wrapper around the llama.cpp server REST API for server management."""

from __future__ import annotations

import logging

import httpx

from ..exceptions import LlamaCppConnectionError
from ..models import LlamaCppServerInfo

logger = logging.getLogger(__name__)


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
        except httpx.HTTPError as e:
            raise LlamaCppConnectionError(
                f"Cannot get server props: {e}"
            ) from e

    async def get_slots(self) -> list[dict]:
        """Fetch active inference slot information.

        Raises:
            LlamaCppConnectionError: If the server is unreachable.
        """
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self._base_url}/slots", timeout=10)
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPError as e:
            raise LlamaCppConnectionError(
                f"Cannot get slot info: {e}"
            ) from e

    async def list_models(self) -> list[str]:
        """Fetch model names via the OpenAI-compatible /v1/models endpoint.

        Returns:
            List of model ID strings.

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
                return [m["id"] for m in data.get("data", [])]
        except httpx.HTTPError as e:
            raise LlamaCppConnectionError(
                f"Cannot list models: {e}"
            ) from e

    async def get_server_info(self) -> LlamaCppServerInfo:
        """Aggregate health, props, and slots into a single server info object.

        Raises:
            LlamaCppConnectionError: If any endpoint is unreachable.
        """
        status = await self.health()
        props = await self.get_props()
        slots = await self.get_slots()

        total_slots = len(slots)
        idle_slots = sum(1 for s in slots if s.get("state") == 0)

        return LlamaCppServerInfo(
            server_url=self._base_url,
            health_status=status,
            model_name=props.get("default_generation_settings", {}).get(
                "model", "unknown"
            ),
            total_slots=total_slots,
            idle_slots=idle_slots,
            ctx_size=props.get("default_generation_settings", {}).get(
                "n_ctx", 0
            ),
        )
