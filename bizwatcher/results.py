from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path

from .models import JudgeResult, RunMetadata, TestResult


def _sanitize_model_name(model: str) -> str:
    return re.sub(r"[/:\\]", "_", model)


def get_next_run_id(results_dir: str, model: str) -> str:
    model_dir = Path(results_dir) / _sanitize_model_name(model)
    if not model_dir.exists():
        return "run_001"

    existing = [
        d.name for d in model_dir.iterdir() if d.is_dir() and d.name.startswith("run_")
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


def load_result(run_dir: Path, test_id: str) -> TestResult:
    path = run_dir / f"{test_id}.json"
    with open(path) as f:
        return TestResult(**json.load(f))


def load_metadata(run_dir: Path) -> RunMetadata:
    path = run_dir / "metadata.json"
    with open(path) as f:
        return RunMetadata(**json.load(f))


def load_all_results(run_dir: Path) -> list[TestResult]:
    results = []
    for path in sorted(run_dir.glob("*.json")):
        if path.name == "metadata.json" or path.name.endswith(".judge.json"):
            continue
        with open(path) as f:
            results.append(TestResult(**json.load(f)))
    return results


def save_judge_result(run_dir: Path, result: JudgeResult) -> None:
    path = run_dir / f"{result.test_id}.judge.json"
    with open(path, "w") as f:
        json.dump(asdict(result), f, indent=2)


def load_judge_result(run_dir: Path, test_id: str) -> JudgeResult | None:
    path = run_dir / f"{test_id}.judge.json"
    if not path.exists():
        return None
    with open(path) as f:
        return JudgeResult(**json.load(f))


def load_all_judge_results(run_dir: Path) -> dict[str, JudgeResult]:
    results = {}
    for path in sorted(run_dir.glob("*.judge.json")):
        with open(path) as f:
            jr = JudgeResult(**json.load(f))
            results[jr.test_id] = jr
    return results
