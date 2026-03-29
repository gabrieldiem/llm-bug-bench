"""Routes for exporting run results and leaderboard data as CSV or Markdown."""

from __future__ import annotations

import csv
import io
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from ...core.leaderboard import compute_leaderboard, sort_leaderboard
from ...core.results import load_all_judge_results, load_all_results, load_metadata
from ..dependencies import get_results_dir

router = APIRouter()


@router.get("/api/export/{model_slug}/{run_id}/csv")
def export_run_csv(
    model_slug: str,
    run_id: str,
    results_dir: str = Depends(get_results_dir),
):
    """Download a run's results as a CSV file."""
    run_dir = Path(results_dir) / model_slug / run_id
    meta = load_metadata(run_dir)
    results = load_all_results(run_dir)
    judge_results = load_all_judge_results(run_dir)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "test_id",
            "elapsed_seconds",
            "tokens_per_second",
            "prompt_tokens",
            "completion_tokens",
            "total_tokens",
            "score",
            "explanation",
            "error",
        ]
    )

    for r in results:
        jr = judge_results.get(r.test_id)
        writer.writerow(
            [
                r.test_id,
                r.elapsed_seconds,
                r.tokens_per_second or "",
                r.prompt_tokens or "",
                r.completion_tokens or "",
                r.total_tokens or "",
                jr.score if jr else "",
                jr.explanation if jr else "",
                r.error or "",
            ]
        )

    buf.seek(0)
    filename = f"{meta.model}_{run_id}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/export/{model_slug}/{run_id}/markdown")
def export_run_markdown(
    model_slug: str,
    run_id: str,
    results_dir: str = Depends(get_results_dir),
):
    """Download a run's results as a Markdown report."""
    run_dir = Path(results_dir) / model_slug / run_id
    meta = load_metadata(run_dir)
    results = load_all_results(run_dir)
    judge_results = load_all_judge_results(run_dir)

    lines = [
        f"# Benchmark Results: {meta.model} — {meta.run_id}",
        "",
        f"- **Model:** {meta.model}",
        f"- **Timestamp:** {meta.timestamp[:19].replace('T', ' ')}",
        f"- **Tests:** {meta.total_tests}",
        f"- **Total elapsed:** {meta.total_elapsed_seconds}s",
        f"- **Avg tok/s:** {meta.avg_tokens_per_second or 'N/A'}",
        f"- **Temperature:** {meta.temperature}",
        "",
        "| Test ID | Elapsed | tok/s | Score | Error |",
        "|---------|---------|-------|-------|-------|",
    ]

    for r in results:
        jr = judge_results.get(r.test_id)
        score_str = str(jr.score) if jr else "—"
        error_str = r.error[:50] if r.error else ""
        tps_str = str(r.tokens_per_second) if r.tokens_per_second else "—"
        lines.append(
            f"| {r.test_id} | {r.elapsed_seconds}s | {tps_str} | {score_str} | {error_str} |"
        )

    lines.append("")
    content = "\n".join(lines)
    filename = f"{meta.model}_{run_id}.md"
    return StreamingResponse(
        iter([content]),
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/api/export/leaderboard/csv")
def export_leaderboard_csv(
    results_dir: str = Depends(get_results_dir),
):
    """Download the leaderboard as a CSV file."""
    entries = compute_leaderboard(results_dir)
    entries = sort_leaderboard(entries, sort_by="score", descending=True)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "model",
            "provider",
            "best_avg_score",
            "latest_avg_score",
            "avg_tokens_per_second",
            "total_runs",
        ]
    )
    for e in entries:
        writer.writerow(
            [
                e.model,
                e.provider,
                e.best_avg_score or "",
                e.latest_avg_score or "",
                e.avg_tokens_per_second or "",
                e.total_runs,
            ]
        )

    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="leaderboard.csv"'},
    )
