"""Shared fixtures for endpoint tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from src.web.app import create_app


@pytest.fixture()
def tmp_dirs(tmp_path: Path):
    """Create temporary results and benchmarks directories."""
    results = tmp_path / "results"
    benchmarks = tmp_path / "benchmarks"
    results.mkdir()
    benchmarks.mkdir()
    return results, benchmarks


@pytest.fixture()
def app(tmp_dirs):
    """Create a FastAPI app with isolated temp directories."""
    results, benchmarks = tmp_dirs
    return create_app(results_dir=str(results), benchmarks_dir=str(benchmarks))


@pytest.fixture()
def client(app):
    """TestClient wrapping the app."""
    return TestClient(app)


@pytest.fixture()
def sample_benchmark(tmp_dirs):
    """Write a minimal YAML benchmark case and return its data."""
    _, benchmarks = tmp_dirs
    lang_dir = benchmarks / "python"
    lang_dir.mkdir()

    data = {
        "id": "py_test_001",
        "title": "Sample test case",
        "language": "python",
        "difficulty": "easy",
        "prompt": "Find the bug in this code.",
        "code": "x = []\nx.append(1)\nprint(x[2])",
        "expected_issues": ["IndexError: list index out of range"],
    }
    with open(lang_dir / "py_test_001.yaml", "w") as f:
        yaml.dump(data, f)

    return data


@pytest.fixture()
def sample_run(tmp_dirs):
    """Write a fake run with metadata and one result, return (model_slug, run_id)."""
    results, _ = tmp_dirs
    model_slug = "test-model"
    run_id = "run_001"
    run_dir = results / model_slug / run_id
    run_dir.mkdir(parents=True)

    metadata = {
        "run_id": run_id,
        "model": "test-model",
        "api_url": "http://localhost:11434/v1",
        "timestamp": "2025-01-01T00:00:00+00:00",
        "temperature": 0.1,
        "max_tokens": 2048,
        "total_tests": 1,
        "total_elapsed_seconds": 2.5,
        "avg_tokens_per_second": 50.0,
        "test_ids": ["py_test_001"],
        "provider": "ollama",
        "system_prompt": "You are a code reviewer.",
        "think": False,
    }
    with open(run_dir / "metadata.json", "w") as f:
        json.dump(metadata, f)

    result = {
        "test_id": "py_test_001",
        "model": "test-model",
        "prompt_sent": "[SYSTEM] prompt [USER] find bug",
        "response": "There is an IndexError on line 3.",
        "prompt_tokens": 50,
        "completion_tokens": 20,
        "total_tokens": 70,
        "elapsed_seconds": 2.5,
        "tokens_per_second": 50.0,
        "timestamp": "2025-01-01T00:00:00+00:00",
        "error": None,
    }
    with open(run_dir / "py_test_001.json", "w") as f:
        json.dump(result, f)

    return model_slug, run_id
