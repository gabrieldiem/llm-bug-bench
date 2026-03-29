"""Filesystem persistence for test results, run metadata, and judge scores."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict
from pathlib import Path

from ..models import JudgeResult, RunMetadata, TestResult

logger = logging.getLogger(__name__)


def _sanitize_model_name(model: str) -> str:
    """Replace filesystem-unsafe characters in model names with underscores."""
    return re.sub(r"[/:\\]", "_", model)


def get_next_run_id(results_dir: str, model: str) -> str:
    """Compute the next sequential run ID (e.g. run_001, run_002)."""
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
    """Create the run output directory and return its path."""
    run_dir = Path(results_dir) / _sanitize_model_name(model) / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Run directory created: %s", run_dir)
    return run_dir


def save_result(run_dir: Path, result: TestResult) -> None:
    """Write a single test result as JSON."""
    path = run_dir / f"{result.test_id}.json"
    with open(path, "w") as f:
        json.dump(asdict(result), f, indent=2)
    logger.debug("Result saved: %s", path)


def save_metadata(run_dir: Path, metadata: RunMetadata) -> None:
    """Write run metadata as JSON."""
    path = run_dir / "metadata.json"
    with open(path, "w") as f:
        json.dump(asdict(metadata), f, indent=2)
    logger.debug("Metadata saved: %s", path)


def load_result(run_dir: Path, test_id: str) -> TestResult:
    """Load a single test result from JSON."""
    path = run_dir / f"{test_id}.json"
    with open(path) as f:
        return TestResult(**json.load(f))


def load_metadata(run_dir: Path) -> RunMetadata:
    """Load run metadata from JSON."""
    path = run_dir / "metadata.json"
    with open(path) as f:
        data = json.load(f)
        valid_fields = {
            field.name for field in RunMetadata.__dataclass_fields__.values()
        }
        data = {k: v for k, v in data.items() if k in valid_fields}
        return RunMetadata(**data)


def load_all_results(run_dir: Path) -> list[TestResult]:
    """Load all test results from a run directory (excludes metadata and judge files)."""
    results = []
    for path in sorted(run_dir.glob("*.json")):
        if path.name == "metadata.json" or path.name.endswith(".judge.json"):
            continue
        with open(path) as f:
            results.append(TestResult(**json.load(f)))
    return results


def save_judge_result(run_dir: Path, result: JudgeResult) -> None:
    """Write a judge evaluation result as JSON."""
    path = run_dir / f"{result.test_id}.judge.json"
    with open(path, "w") as f:
        json.dump(asdict(result), f, indent=2)
    logger.debug("Judge result saved: %s", path)


def load_judge_result(run_dir: Path, test_id: str) -> JudgeResult | None:
    """Load a judge result for a test, or None if not yet judged."""
    path = run_dir / f"{test_id}.judge.json"
    if not path.exists():
        return None
    with open(path) as f:
        return JudgeResult(**json.load(f))


def load_all_judge_results(run_dir: Path) -> dict[str, JudgeResult]:
    """Load all judge results from a run directory, keyed by test_id."""
    results = {}
    for path in sorted(run_dir.glob("*.judge.json")):
        with open(path) as f:
            jr = JudgeResult(**json.load(f))
            results[jr.test_id] = jr
    return results


def delete_run(run_dir: Path) -> None:
    """Recursively delete a run directory and all its contents."""
    import shutil

    if run_dir.exists():
        shutil.rmtree(run_dir)
        logger.info("Run deleted: %s", run_dir)
