from __future__ import annotations

import argparse
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from .results import load_all_judge_results, load_all_results, load_metadata

_TEMPLATES_DIR = Path(__file__).parent / "templates"


def create_app(results_dir: str) -> FastAPI:
    app = FastAPI(title="bizantine-watcher")
    templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

    @app.get("/", response_class=HTMLResponse)
    def handle_dashboard(request: Request):
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
                    "model_slug": run_dir.parent.name,
                }
            )
        runs.sort(key=lambda r: r["timestamp"], reverse=True)
        return templates.TemplateResponse(
            "dashboard.html", {"request": request, "runs": runs}
        )

    @app.get("/run/{model_slug}/{run_id}", response_class=HTMLResponse)
    def handle_run_detail(model_slug: str, run_id: str, request: Request):
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
                    "score": jr.score if jr else None,
                    "error": r.error,
                    "model_slug": model_slug,
                    "run_id": run_id,
                }
            )
        return templates.TemplateResponse(
            "run_detail.html",
            {"request": request, "meta": meta, "rows": rows, "model_slug": model_slug},
        )

    @app.get("/run/{model_slug}/{run_id}/{test_id}", response_class=HTMLResponse)
    def handle_test_detail(
        model_slug: str, run_id: str, test_id: str, request: Request
    ):
        from .results import load_judge_result, load_result

        run_dir = Path(results_dir) / model_slug / run_id
        result = load_result(run_dir, test_id)
        jr = load_judge_result(run_dir, test_id)
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

    return app


def serve(args: argparse.Namespace) -> None:
    app = create_app(args.results_dir)
    uvicorn.run(app, host="0.0.0.0", port=args.port)
