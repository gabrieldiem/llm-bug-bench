from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ...core.judge import DEFAULT_JUDGE_MODEL, judge_run
from ..dependencies import get_results_dir, get_task_manager, get_tests_dir
from ..task_manager import TaskManager

router = APIRouter()


@router.post("/api/judge/{model_slug}/{run_id}")
async def api_start_judge(
    model_slug: str,
    run_id: str,
    request: Request,
    task_manager: TaskManager = Depends(get_task_manager),
    results_dir: str = Depends(get_results_dir),
    tests_dir: str = Depends(get_tests_dir),
):
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    api_key = body.get("api_key", "") or os.environ.get("OPENAI_API_KEY", "")
    judge_model = body.get("judge_model", "") or DEFAULT_JUDGE_MODEL

    if not api_key:
        return JSONResponse(
            {
                "error": "OPENAI_API_KEY not set. Provide api_key in request or set the env var."
            },
            status_code=400,
        )

    run_dir = Path(results_dir) / model_slug / run_id
    if not run_dir.exists():
        return JSONResponse({"error": "Run not found"}, status_code=404)

    task_id = task_manager.create_task_id()
    progress_cb = task_manager.make_progress_callback(task_id)

    async def _judge():
        await asyncio.to_thread(
            judge_run, run_dir, tests_dir, judge_model, api_key, task_id, progress_cb
        )

    task_manager.submit(task_id, _judge())

    return JSONResponse({"task_id": task_id})


@router.get("/api/judge/{task_id}/progress")
async def api_judge_progress(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager),
):
    entry = task_manager.get_entry(task_id)
    if not entry:
        return JSONResponse({"error": "Task not found"}, status_code=404)

    async def _stream():
        while True:
            try:
                progress = await asyncio.wait_for(
                    entry.progress_queue.get(), timeout=30
                )
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'status': 'heartbeat'})}\n\n"
                continue

            if progress is None:
                exc = entry.task.exception() if entry.task.done() else None
                if exc:
                    yield f"data: {json.dumps({'status': 'failed', 'error': str(exc)})}\n\n"
                else:
                    yield f"data: {json.dumps({'status': 'done'})}\n\n"
                break

            yield f"data: {json.dumps(asdict(progress))}\n\n"

            if progress.status in ("completed", "failed"):
                break

    return StreamingResponse(_stream(), media_type="text/event-stream")
