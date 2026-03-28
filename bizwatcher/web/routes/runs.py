from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from ...core.results import (
    load_all_judge_results,
    load_all_results,
    load_judge_result,
    load_metadata,
    load_result,
)
from ..dependencies import get_results_dir

router = APIRouter()


@router.get("/run/{model_slug}/{run_id}", response_class=HTMLResponse)
def handle_run_detail(
    model_slug: str,
    run_id: str,
    request: Request,
    results_dir: str = Depends(get_results_dir),
):
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
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "run_detail.html",
        {
            "request": request,
            "meta": meta,
            "rows": rows,
            "model_slug": model_slug,
            "has_unjudged": any(r["score"] is None for r in rows),
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
