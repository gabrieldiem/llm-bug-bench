"""Routes for triggering LLM judge scoring with background execution and SSE progress."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse

from ...core.judge import DEFAULT_JUDGE_MODEL, judge_run
from ..dependencies import get_results_dir, get_task_manager, get_benchmarks_dir
from ..task_manager import TaskManager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/judge/{model_slug}/{run_id}")
async def api_start_judge(
    model_slug: str,
    run_id: str,
    request: Request,
    task_manager: TaskManager = Depends(get_task_manager),
    results_dir: str = Depends(get_results_dir),
    benchmarks_dir: str = Depends(get_benchmarks_dir),
):
    """Start judging a run as a background task. Returns task_id for SSE tracking."""
    body = {}
    try:
        body = await request.json()
    except Exception:
        pass

    api_key = body.get("api_key", "") or os.environ.get("OPENAI_API_KEY", "")
    judge_model = body.get("judge_model", "") or DEFAULT_JUDGE_MODEL
    force = bool(body.get("force", False))

    if not api_key:
        logger.warning("Judge rejected: OPENAI_API_KEY not set")
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
    run_key = f"{model_slug}/{run_id}"

    logger.info(
        "Judge started via API: %s/%s model=%s task_id=%s",
        model_slug,
        run_id,
        judge_model,
        task_id,
    )

    async def _judge():
        await asyncio.to_thread(
            judge_run,
            run_dir,
            benchmarks_dir,
            judge_model,
            api_key,
            task_id,
            progress_cb,
            force,
        )

    task_manager.submit(task_id, _judge())
    task_manager.register_judge_task(run_key, task_id)

    return JSONResponse({"task_id": task_id})


@router.get("/api/judge/{model_slug}/{run_id}/active")
async def api_active_judge(
    model_slug: str,
    run_id: str,
    task_manager: TaskManager = Depends(get_task_manager),
):
    """Return the active judge task_id for this run, if one is running."""
    run_key = f"{model_slug}/{run_id}"
    task_id = task_manager.get_active_judge_task(run_key)
    if not task_id:
        return JSONResponse({"error": "No active judge task"}, status_code=404)
    return JSONResponse({"task_id": task_id})


@router.get("/api/judge/{task_id}/progress")
async def api_judge_progress(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager),
):
    """Stream judge progress events via SSE, replaying full history on connect."""
    entry = task_manager.get_entry(task_id)
    if not entry:
        return JSONResponse({"error": "Task not found"}, status_code=404)

    queue = task_manager.subscribe(task_id)

    async def _stream():
        while True:
            try:
                progress = await asyncio.wait_for(queue.get(), timeout=30)
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
