from __future__ import annotations

from fastapi import Request

from .task_manager import TaskManager


def get_results_dir(request: Request) -> str:
    return request.app.state.results_dir


def get_tests_dir(request: Request) -> str:
    return request.app.state.tests_dir


def get_task_manager(request: Request) -> TaskManager:
    return request.app.state.task_manager


def get_ollama_url(request: Request) -> str:
    return request.app.state.ollama_url
