from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from typing import Any

from ..models import RunProgress


@dataclass
class TaskEntry:
    task_id: str
    task: asyncio.Task[Any]
    progress_queue: asyncio.Queue[RunProgress | None]
    status: str = "pending"


class TaskManager:
    """Manages background asyncio tasks with SSE progress queues."""

    def __init__(self) -> None:
        self._tasks: dict[str, TaskEntry] = {}

    def create_task_id(self) -> str:
        return uuid.uuid4().hex[:12]

    def submit(
        self,
        task_id: str,
        coro: Any,
    ) -> TaskEntry:
        queue: asyncio.Queue[RunProgress | None] = asyncio.Queue()
        task = asyncio.create_task(coro)
        entry = TaskEntry(
            task_id=task_id, task=task, progress_queue=queue, status="running"
        )
        self._tasks[task_id] = entry

        task.add_done_callback(lambda _t: self._on_done(task_id))
        return entry

    def get_entry(self, task_id: str) -> TaskEntry | None:
        return self._tasks.get(task_id)

    def make_progress_callback(self, task_id: str):
        """Return a sync callback that puts RunProgress onto the task's queue."""
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
        entry = self._tasks.get(task_id)
        if entry:
            entry.status = "completed" if not entry.task.cancelled() else "failed"
            try:
                entry.progress_queue.put_nowait(None)
            except asyncio.QueueFull:
                pass
