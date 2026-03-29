from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from ...core.results import (
    load_all_judge_results,
    load_all_results,
    load_metadata,
)
from ..dependencies import get_results_dir

router = APIRouter()


@router.get("/compare", response_class=HTMLResponse)
def handle_compare_form(
    request: Request,
    results_dir: str = Depends(get_results_dir),
):
    results_path = Path(results_dir)
    runs = []
    for meta_path in sorted(results_path.glob("*/run_*/metadata.json")):
        run_dir = meta_path.parent
        try:
            meta = load_metadata(run_dir)
        except Exception:
            continue
        runs.append(
            {
                "model": meta.model,
                "run_id": meta.run_id,
                "model_slug": run_dir.parent.name,
                "label": f"{meta.model} / {meta.run_id}",
            }
        )
    runs.sort(key=lambda r: (r["model"], r["run_id"]))

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "compare.html",
        {"request": request, "runs": runs, "comparison": None},
    )


@router.get("/compare/{slug_a}/{run_a}/{slug_b}/{run_b}", response_class=HTMLResponse)
def handle_compare_view(
    slug_a: str,
    run_a: str,
    slug_b: str,
    run_b: str,
    request: Request,
    results_dir: str = Depends(get_results_dir),
):
    results_path = Path(results_dir)

    dir_a = results_path / slug_a / run_a
    dir_b = results_path / slug_b / run_b
    meta_a = load_metadata(dir_a)
    meta_b = load_metadata(dir_b)

    results_a = {r.test_id: r for r in load_all_results(dir_a)}
    results_b = {r.test_id: r for r in load_all_results(dir_b)}
    judge_a = load_all_judge_results(dir_a)
    judge_b = load_all_judge_results(dir_b)

    all_test_ids = sorted(set(results_a.keys()) | set(results_b.keys()))

    rows = []
    for tid in all_test_ids:
        ra = results_a.get(tid)
        rb = results_b.get(tid)
        ja = judge_a.get(tid)
        jb = judge_b.get(tid)

        score_a = ja.score if ja else None
        score_b = jb.score if jb else None

        winner = None
        if score_a is not None and score_b is not None:
            if score_a > score_b:
                winner = "a"
            elif score_b > score_a:
                winner = "b"

        rows.append(
            {
                "test_id": tid,
                "elapsed_a": ra.elapsed_seconds if ra else None,
                "elapsed_b": rb.elapsed_seconds if rb else None,
                "tps_a": ra.tokens_per_second if ra else None,
                "tps_b": rb.tokens_per_second if rb else None,
                "score_a": score_a,
                "score_b": score_b,
                "winner": winner,
            }
        )

    # Available runs for the selector
    runs = []
    for meta_path in sorted(results_path.glob("*/run_*/metadata.json")):
        run_dir = meta_path.parent
        try:
            meta = load_metadata(run_dir)
        except Exception:
            continue
        runs.append(
            {
                "model": meta.model,
                "run_id": meta.run_id,
                "model_slug": run_dir.parent.name,
                "label": f"{meta.model} / {meta.run_id}",
            }
        )
    runs.sort(key=lambda r: (r["model"], r["run_id"]))

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "compare.html",
        {
            "request": request,
            "runs": runs,
            "comparison": {
                "meta_a": meta_a,
                "meta_b": meta_b,
                "slug_a": slug_a,
                "run_a": run_a,
                "slug_b": slug_b,
                "run_b": run_b,
                "rows": rows,
            },
        },
    )
