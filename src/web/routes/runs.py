"""Routes for benchmark runs — new run form, execution, progress SSE, and detail views."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import asdict
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse

from ...core.results import (
    delete_run,
    load_all_judge_results,
    load_all_results,
    load_judge_result,
    load_metadata,
    load_result,
)
from ...core.runner import DEFAULT_SYSTEM_PROMPT, run_with_config
from ...models import ProviderConfig, RunConfig
from ..dependencies import (
    get_ollama_url,
    get_results_dir,
    get_task_manager,
    get_benchmarks_dir,
)
from ..task_manager import TaskManager

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------


@router.get("/runs/new", response_class=HTMLResponse)
async def handle_new_run_form(
    request: Request,
    benchmarks_dir: str = Depends(get_benchmarks_dir),
    ollama_url: str = Depends(get_ollama_url),
):
    """Render the new run configuration form."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "runs/new.html",
        {
            "request": request,
            "default_system_prompt": DEFAULT_SYSTEM_PROMPT,
            "ollama_url": ollama_url,
        },
    )


@router.get("/runs/progress/{task_id}", response_class=HTMLResponse)
async def handle_run_progress_page(
    task_id: str,
    request: Request,
):
    """Render the run progress tracking page."""
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "runs/progress.html",
        {"request": request, "task_id": task_id},
    )


@router.get("/run/{model_slug}/{run_id}", response_class=HTMLResponse)
def handle_run_detail(
    model_slug: str,
    run_id: str,
    request: Request,
    results_dir: str = Depends(get_results_dir),
    sort: str = "test_id",
    order: str = "asc",
):
    """Render the run detail page with per-test results and scores."""
    run_dir = Path(results_dir) / model_slug / run_id
    meta = load_metadata(run_dir)
    results = load_all_results(run_dir)
    judge_results = load_all_judge_results(run_dir)
    rows = []
    for r in results:
        jr = judge_results.get(r.test_id)
        rows.append(
            {
                "test_id": r.test_id,
                "elapsed_seconds": r.elapsed_seconds,
                "tokens_per_second": r.tokens_per_second,
                "score": jr.score if jr else None,
                "error": r.error,
                "model_slug": model_slug,
                "run_id": run_id,
            }
        )

    key_map: dict = {
        "test_id": lambda r: r["test_id"].lower(),
        "elapsed": lambda r: r["elapsed_seconds"] or 0,
        "tps": lambda r: r["tokens_per_second"] or 0,
        "score": lambda r: r["score"] or 0,
    }
    key_fn = key_map.get(sort, key_map["test_id"])
    rows.sort(key=key_fn, reverse=(order == "desc"))

    is_htmx = request.headers.get("HX-Request") == "true"
    template = "partials/_run_table.html" if is_htmx else "run_detail.html"

    templates = request.app.state.templates
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "meta": meta,
            "rows": rows,
            "model_slug": model_slug,
            "has_unjudged": any(r["score"] is None for r in rows),
            "sort": sort,
            "order": order,
        },
    )


@router.get("/run/{model_slug}/{run_id}/{test_id}", response_class=HTMLResponse)
def handle_test_detail(
    model_slug: str,
    run_id: str,
    test_id: str,
    request: Request,
    results_dir: str = Depends(get_results_dir),
):
    """Render the test detail page with prompt, response, and judge evaluation."""
    run_dir = Path(results_dir) / model_slug / run_id
    result = load_result(run_dir, test_id)
    jr = load_judge_result(run_dir, test_id)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "test_detail.html",
        {
            "request": request,
            "result": result,
            "jr": jr,
            "model_slug": model_slug,
            "run_id": run_id,
        },
    )


# ---------------------------------------------------------------------------
# API routes
# ---------------------------------------------------------------------------


@router.post("/api/runs")
async def api_start_run(
    request: Request,
    task_manager: TaskManager = Depends(get_task_manager),
    results_dir: str = Depends(get_results_dir),
    benchmarks_dir: str = Depends(get_benchmarks_dir),
    ollama_url: str = Depends(get_ollama_url),
):
    """Start a benchmark run as a background task. Returns task_id for SSE tracking."""
    body = await request.json()

    provider = body.get("provider", "ollama")
    model = body.get("model", "")
    api_key = body.get("api_key", "")
    api_url = body.get("api_url", "")

    if not model:
        logger.warning("Run rejected: model name is required")
        return JSONResponse({"error": "Model name is required"}, status_code=400)

    if provider == "ollama":
        api_url = api_url or f"{ollama_url}/v1"
    elif provider == "openai":
        api_url = "https://api.openai.com/v1"
        if not api_key:
            logger.warning("Run rejected: OpenAI API key required")
            return JSONResponse(
                {"error": "API key is required for OpenAI"}, status_code=400
            )
    elif provider == "gemini":
        api_url = "https://generativelanguage.googleapis.com/v1beta/openai/"
        if not api_key:
            logger.warning("Run rejected: Gemini API key required")
            return JSONResponse(
                {"error": "API key is required for Gemini"}, status_code=400
            )
    else:
        return JSONResponse({"error": f"Unknown provider: {provider}"}, status_code=400)

    config = RunConfig(
        provider_config=ProviderConfig(
            provider=provider,
            api_url=api_url,
            api_key=api_key,
            model=model,
        ),
        temperature=float(body.get("temperature", 0.1)),
        max_tokens=int(body.get("max_tokens", 2048)),
        system_prompt=body.get("system_prompt", ""),
        think=bool(body.get("think", False)),
        benchmarks_dir=benchmarks_dir,
        results_dir=results_dir,
    )

    task_id = task_manager.create_task_id()
    progress_cb = task_manager.make_progress_callback(task_id)

    logger.info(
        "Run started via API: model=%s provider=%s task_id=%s",
        model,
        provider,
        task_id,
    )

    async def _run():
        await asyncio.to_thread(run_with_config, config, task_id, progress_cb)

    task_manager.submit(task_id, _run())

    return JSONResponse({"task_id": task_id})


@router.get("/api/runs/{task_id}/progress")
async def api_run_progress(
    task_id: str,
    task_manager: TaskManager = Depends(get_task_manager),
):
    """Stream run progress events via SSE."""
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


@router.delete("/api/runs/{model_slug}/{run_id}")
def api_delete_run(
    model_slug: str,
    run_id: str,
    results_dir: str = Depends(get_results_dir),
):
    """Delete a run directory and all its contents."""
    run_dir = Path(results_dir) / model_slug / run_id
    if not run_dir.exists():
        return JSONResponse({"error": "Run not found"}, status_code=404)
    delete_run(run_dir)
    logger.info("Run deleted via API: %s/%s", model_slug, run_id)
    return JSONResponse({"ok": True})
