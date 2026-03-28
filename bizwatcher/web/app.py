from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.templating import Jinja2Templates

from .task_manager import TaskManager

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    app.state.task_manager = TaskManager()
    yield


def create_app(
    results_dir: str = "./results",
    tests_dir: str = "./tests",
) -> FastAPI:
    app = FastAPI(title="bizantine-watcher", lifespan=_lifespan)

    app.state.results_dir = results_dir
    app.state.tests_dir = tests_dir
    app.state.ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")

    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
    app.state.templates = templates

    from .routes import dashboard, ollama, runs, tests

    app.include_router(dashboard.router)
    app.include_router(runs.router)
    app.include_router(ollama.router)
    app.include_router(tests.router)

    return app
