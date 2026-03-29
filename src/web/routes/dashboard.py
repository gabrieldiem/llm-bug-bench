"""Dashboard route — main landing page with all runs and quick stats."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from ...core.results import load_all_judge_results, load_metadata
from ..dependencies import get_results_dir

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def handle_dashboard(
    request: Request,
    results_dir: str = Depends(get_results_dir),
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
    runs.sort(key=lambda r: r["timestamp"], reverse=True)

    total_models = len({r["model"] for r in runs})
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "runs": runs,
            "total_models": total_models,
            "total_runs": len(runs),
        },
    )
