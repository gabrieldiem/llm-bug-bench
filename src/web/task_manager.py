"""Background task management with pub/sub history queues for SSE progress streaming."""

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
    """Tracks a single background asyncio task with a broadcast history for SSE replay."""

    task_id: str
    task: asyncio.Task[Any]
    status: str = "pending"
    history: list[RunProgress] = field(default_factory=list)
    subscribers: list[asyncio.Queue[RunProgress | None]] = field(default_factory=list)
    done: bool = False
    meta: dict[str, Any] = field(default_factory=dict)


class TaskManager:
    """Manages background asyncio tasks with pub/sub SSE progress queues.

    Every progress event is stored in the task's history list and broadcast to
    all active subscriber queues. A new subscriber (e.g. after a page reload)
    receives the full history replayed first, then live events going forward.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, TaskEntry] = {}
        self._judge_tasks: dict[str, str] = {}  # "model_slug/run_id" → task_id

    def create_task_id(self) -> str:
        """Generate a unique 12-character hex task ID."""
        return uuid.uuid4().hex[:12]

    def submit(self, task_id: str, coro: Any) -> TaskEntry:
        """Submit an async coroutine as a background task.

        Args:
            task_id: Unique identifier for the task.
            coro: Async coroutine to execute.

        Returns:
            TaskEntry for the submitted task.
        """
        task = asyncio.create_task(coro)
        entry = TaskEntry(task_id=task_id, task=task, status="running")
        self._tasks[task_id] = entry
        task.add_done_callback(lambda _t: self._on_done(task_id))
        logger.info("Task submitted: %s", task_id)
        return entry

    def get_entry(self, task_id: str) -> TaskEntry | None:
        """Look up a task by ID, or return None if not found."""
        return self._tasks.get(task_id)

    def subscribe(self, task_id: str) -> asyncio.Queue[RunProgress | None] | None:
        """Return a new queue pre-populated with the full event history.

        If the task is already done the terminal None sentinel is queued
        immediately so the caller's read loop terminates normally.
        If the task is still running, the queue is registered as a subscriber
        and will receive all future events.

        Returns None if the task_id is unknown.
        """
        entry = self._tasks.get(task_id)
        if not entry:
            return None
        q: asyncio.Queue[RunProgress | None] = asyncio.Queue()
        for event in entry.history:
            q.put_nowait(event)
        if entry.done:
            q.put_nowait(None)
        else:
            entry.subscribers.append(q)
        return q

    def make_progress_callback(self, task_id: str):
        """Return a sync callback that publishes a RunProgress event.

        The returned function is safe to call from a worker thread (via
        asyncio.to_thread()) — it uses loop.call_soon_threadsafe() to
        schedule the actual history append and queue broadcast on the event
        loop, which is the only thread-safe way to wake asyncio waiters.
        """
        loop = asyncio.get_running_loop()

        def _publish(progress: RunProgress) -> None:
            """Runs on the event loop — safe to mutate history and queues."""
            entry = self._tasks.get(task_id)
            if not entry:
                return
            entry.history.append(progress)
            for q in list(entry.subscribers):
                try:
                    q.put_nowait(progress)
                except asyncio.QueueFull:
                    pass

        def _cb(progress: RunProgress) -> None:
            """Called from a worker thread — hands off to the event loop."""
            loop.call_soon_threadsafe(_publish, progress)

        return _cb

    def running_task_ids(self) -> list[str]:
        """Return task IDs of all tasks currently in the 'running' state."""
        return [tid for tid, e in self._tasks.items() if e.status == "running"]

    def register_judge_task(self, run_key: str, task_id: str) -> None:
        """Record that a judge task is running for the given run key."""
        self._judge_tasks[run_key] = task_id

    def get_active_judge_task(self, run_key: str) -> str | None:
        """Return the task_id of an active judge task for this run, or None."""
        task_id = self._judge_tasks.get(run_key)
        if not task_id:
            return None
        entry = self._tasks.get(task_id)
        if entry and entry.status == "running":
            return task_id
        return None

    def _on_done(self, task_id: str) -> None:
        """Mark a task as complete and broadcast the terminal sentinel."""
        entry = self._tasks.get(task_id)
        if entry:
            entry.status = "completed" if not entry.task.cancelled() else "failed"
            entry.done = True
            logger.info("Task %s: %s", entry.status, task_id)
            for q in list(entry.subscribers):
                try:
                    q.put_nowait(None)
                except asyncio.QueueFull:
                    pass
            entry.subscribers.clear()
