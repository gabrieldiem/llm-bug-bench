"""Dashboard route — main landing page with all runs and quick stats."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from ...core.results import load_all_judge_results, load_metadata
from ..dependencies import get_results_dir

router = APIRouter()


@router.get("/health")
def health_check():
    """Liveness probe for Docker healthcheck."""
    return {"status": "ok"}


@router.get("/", response_class=HTMLResponse)
def handle_dashboard(
    request: Request,
    results_dir: str = Depends(get_results_dir),
    sort: str = "timestamp",
    order: str = "desc",
):
    """Render the main dashboard with all runs, scores, and summary stats."""
    results_path = Path(results_dir)
    runs = []
    for meta_path in sorted(results_path.glob("*/run_*/metadata.json")):
        run_dir = meta_path.parent
        try:
            meta = load_metadata(run_dir)
        except Exception:
            continue
        judge_results = load_all_judge_results(run_dir)
        avg_score = None
        if judge_results:
            avg_score = round(
                sum(jr.score for jr in judge_results.values()) / len(judge_results),
                1,
            )
        runs.append(
            {
                "model": meta.model,
                "run_id": meta.run_id,
                "timestamp": meta.timestamp,
                "total_tests": meta.total_tests,
                "avg_score": avg_score,
                "avg_tps": meta.avg_tokens_per_second,
                "model_slug": run_dir.parent.name,
            }
        )

    key_map: dict = {
        "model": lambda r: r["model"].lower(),
        "run_id": lambda r: r["run_id"].lower(),
        "timestamp": lambda r: r["timestamp"],
        "tests": lambda r: r["total_tests"],
        "tps": lambda r: r["avg_tps"] or 0,
        "score": lambda r: r["avg_score"] or 0,
    }
    key_fn = key_map.get(sort, key_map["timestamp"])
    runs.sort(key=key_fn, reverse=(order == "desc"))

    total_models = len({r["model"] for r in runs})

    is_htmx = request.headers.get("HX-Request") == "true"
    template = "partials/_dashboard_table.html" if is_htmx else "dashboard.html"

    templates = request.app.state.templates
    return templates.TemplateResponse(
        template,
        {
            "request": request,
            "runs": runs,
            "total_models": total_models,
            "total_runs": len(runs),
            "sort": sort,
            "order": order,
        },
    )
