"""FastAPI application factory and router registration."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

from .task_manager import TaskManager

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def create_app(
    results_dir: str = "./results",
    benchmarks_dir: str = "./benchmarks",
) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        results_dir: Directory for storing benchmark results.
        benchmarks_dir: Directory containing YAML benchmark case files.

    Returns:
        Configured FastAPI app with all routers registered.
    """
    app = FastAPI(title="llm-bug-bench")

    app.state.results_dir = results_dir
    app.state.benchmarks_dir = benchmarks_dir
    app.state.ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    app.state.llamacpp_url = os.environ.get("LLAMACPP_URL", "http://localhost:8095")
    app.state.task_manager = TaskManager()

    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
    app.state.templates = templates

    from .routes import (
        compare,
        dashboard,
        export,
        judge,
        leaderboard,
        llamacpp,
        ollama,
        runs,
        tests,
    )

    app.include_router(dashboard.router)
    app.include_router(runs.router)
    app.include_router(ollama.router)
    app.include_router(llamacpp.router)
    app.include_router(tests.router)
    app.include_router(judge.router)
    app.include_router(leaderboard.router)
    app.include_router(export.router)
    app.include_router(compare.router)

    logger.info(
        "App created: results_dir=%s benchmarks_dir=%s ollama_url=%s llamacpp_url=%s",
        results_dir,
        benchmarks_dir,
        app.state.ollama_url,
        app.state.llamacpp_url,
    )
    return app
