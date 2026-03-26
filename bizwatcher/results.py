from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path

from .models import RunMetadata, TestResult


def _sanitize_model_name(model: str) -> str:
    return re.sub(r"[/:\\]", "_", model)


def get_next_run_id(results_dir: str, model: str) -> str:
    model_dir = Path(results_dir) / _sanitize_model_name(model)
    if not model_dir.exists():
        return "run_001"

    existing = [
        d.name for d in model_dir.iterdir()
        if d.is_dir() and d.name.startswith("run_")
    ]
    if not existing:
        return "run_001"

    max_num = max(int(name.split("_")[1]) for name in existing)
    return f"run_{max_num + 1:03d}"


def create_run_dir(results_dir: str, model: str, run_id: str) -> Path:
    run_dir = Path(results_dir) / _sanitize_model_name(model) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def save_result(run_dir: Path, result: TestResult) -> None:
    path = run_dir / f"{result.test_id}.json"
    with open(path, "w") as f:
        json.dump(asdict(result), f, indent=2)


def save_metadata(run_dir: Path, metadata: RunMetadata) -> None:
    path = run_dir / "metadata.json"
    with open(path, "w") as f:
        json.dump(asdict(metadata), f, indent=2)
