"""Background task management with asyncio queues for SSE progress streaming."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..models import RunProgress

logger = logging.getLogger(__name__)


@dataclass
class TaskEntry:
    """Tracks a single background asyncio task and its progress queue."""

    task_id: str
    task: asyncio.Task[Any]
    progress_queue: asyncio.Queue[RunProgress | None]
    status: str = "pending"


class TaskManager:
    """Manages background asyncio tasks with SSE progress queues.

    Each submitted task gets a unique ID and an asyncio.Queue that
    route handlers can read from to stream progress via SSE.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, TaskEntry] = {}

    def create_task_id(self) -> str:
        """Generate a unique 12-character hex task ID."""
        return uuid.uuid4().hex[:12]

    def submit(
        self,
        task_id: str,
        coro: Any,
    ) -> TaskEntry:
        """Submit an async coroutine as a background task.

        Args:
            task_id: Unique identifier for the task.
            coro: Async coroutine to execute.

        Returns:
            TaskEntry with the running task and its progress queue.
        """
        queue: asyncio.Queue[RunProgress | None] = asyncio.Queue()
        task = asyncio.create_task(coro)
        entry = TaskEntry(
            task_id=task_id, task=task, progress_queue=queue, status="running"
        )
        self._tasks[task_id] = entry

        task.add_done_callback(lambda _t: self._on_done(task_id))
        logger.info("Task submitted: %s", task_id)
        return entry

    def get_entry(self, task_id: str) -> TaskEntry | None:
        """Look up a task by ID, or return None if not found."""
        return self._tasks.get(task_id)

    def make_progress_callback(self, task_id: str):
        """Return a sync callback that puts RunProgress onto the task's queue.

        The returned function is safe to call from any thread via
        asyncio.to_thread().
        """
        entry = self._tasks.get(task_id)
        if not entry:
            return lambda _p: None

        def _cb(progress: RunProgress) -> None:
            try:
                entry.progress_queue.put_nowait(progress)
            except asyncio.QueueFull:
                pass

        return _cb

    def _on_done(self, task_id: str) -> None:
        """Mark a completed task and push a sentinel to its queue."""
        entry = self._tasks.get(task_id)
        if entry:
            entry.status = "completed" if not entry.task.cancelled() else "failed"
            logger.info("Task %s: %s", entry.status, task_id)
            try:
                entry.progress_queue.put_nowait(None)
            except asyncio.QueueFull:
                pass
