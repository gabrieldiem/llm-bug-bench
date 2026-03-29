"""FastAPI dependency injection providers for shared application state."""

from __future__ import annotations

from fastapi import Request

from .task_manager import TaskManager


def get_results_dir(request: Request) -> str:
    """Return the configured results directory path."""
    return request.app.state.results_dir


def get_benchmarks_dir(request: Request) -> str:
    """Return the configured benchmarks directory path."""
    return request.app.state.benchmarks_dir


def get_task_manager(request: Request) -> TaskManager:
    """Return the shared TaskManager instance."""
    return request.app.state.task_manager


def get_ollama_url(request: Request) -> str:
    """Return the current Ollama base URL (may be overridden at runtime)."""
    return request.app.state.ollama_url
