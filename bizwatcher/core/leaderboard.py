from __future__ import annotations

from pathlib import Path

from ..models import LeaderboardEntry
from .results import load_all_judge_results, load_metadata


def compute_leaderboard(results_dir: str) -> list[LeaderboardEntry]:
    """Scan all runs and aggregate into one LeaderboardEntry per model."""
    results_path = Path(results_dir)
    if not results_path.exists():
        return []

    model_data: dict[str, dict] = {}

    for meta_path in sorted(results_path.glob("*/run_*/metadata.json")):
        run_dir = meta_path.parent
        try:
            meta = load_metadata(run_dir)
        except Exception:
            continue

        judge_results = load_all_judge_results(run_dir)
        avg_score = None
        if judge_results:
            avg_score = sum(jr.score for jr in judge_results.values()) / len(
                judge_results
            )

        model_key = meta.model
        if model_key not in model_data:
            model_data[model_key] = {
                "provider": getattr(meta, "provider", "ollama"),
                "runs": [],
            }

        model_data[model_key]["runs"].append(
            {
                "run_id": meta.run_id,
                "timestamp": meta.timestamp,
                "avg_score": avg_score,
                "avg_tps": meta.avg_tokens_per_second,
                "model_slug": run_dir.parent.name,
            }
        )

    entries: list[LeaderboardEntry] = []
    for model, data in model_data.items():
        runs = data["runs"]
        runs.sort(key=lambda r: r["timestamp"])

        scored_runs = [r for r in runs if r["avg_score"] is not None]
        best_run = (
            max(scored_runs, key=lambda r: r["avg_score"]) if scored_runs else None
        )
        latest_run = runs[-1]

        tps_values = [r["avg_tps"] for r in runs if r["avg_tps"] is not None]
        avg_tps = sum(tps_values) / len(tps_values) if tps_values else None

        entries.append(
            LeaderboardEntry(
                model=model,
                provider=data["provider"],
                parameter_size="",
                best_avg_score=round(best_run["avg_score"], 1) if best_run else None,
                latest_avg_score=(
                    round(latest_run["avg_score"], 1)
                    if latest_run["avg_score"] is not None
                    else None
                ),
                avg_tokens_per_second=round(avg_tps, 1) if avg_tps else None,
                total_runs=len(runs),
                best_run_id=(
                    f"{best_run['model_slug']}/{best_run['run_id']}" if best_run else ""
                ),
            )
        )

    return entries


def sort_leaderboard(
    entries: list[LeaderboardEntry],
    sort_by: str = "score",
    descending: bool = True,
) -> list[LeaderboardEntry]:
    """Sort leaderboard entries by the given column."""
    key_map = {
        "score": lambda e: e.best_avg_score or 0,
        "speed": lambda e: e.avg_tokens_per_second or 0,
        "runs": lambda e: e.total_runs,
        "model": lambda e: e.model.lower(),
    }
    key_fn = key_map.get(sort_by, key_map["score"])
    return sorted(entries, key=key_fn, reverse=descending)
