"""YAML test case discovery, loading, and CRUD operations."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from ..exceptions import DuplicateTestIdError, TestNotFoundError
from ..models import TestCase

logger = logging.getLogger(__name__)


def load_tests(benchmarks_dir: str) -> list[TestCase]:
    """Discover and load all YAML test cases.

    Args:
        benchmarks_dir: Root directory to search recursively for *.yaml files.

    Returns:
        Sorted list of TestCase objects (by language, then id).

    Raises:
        FileNotFoundError: If benchmarks_dir does not exist.
    """
    benchmarks_path = Path(benchmarks_dir)
    if not benchmarks_path.is_dir():
        raise FileNotFoundError(f"Tests directory not found: {benchmarks_dir}")

    cases: list[TestCase] = []
    for yaml_file in sorted(benchmarks_path.rglob("*.yaml")):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        if not data:
            logger.warning("Empty YAML file skipped: %s", yaml_file)
            continue

        cases.append(_parse_test_case(data))

    cases.sort(key=lambda c: (c.language, c.id))
    logger.info("Loaded %d test(s) from %s", len(cases), benchmarks_dir)
    return cases


def load_test_by_id(benchmarks_dir: str, test_id: str) -> TestCase:
    """Load a single test case by its ID.

    Raises:
        TestNotFoundError: If no test with the given ID exists.
    """
    benchmarks_path = Path(benchmarks_dir)
    for yaml_file in benchmarks_path.rglob("*.yaml"):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        if data and data.get("id") == test_id:
            return _parse_test_case(data)
    raise TestNotFoundError(f"Test case not found: {test_id}")


def save_test(benchmarks_dir: str, test: TestCase) -> Path:
    """Create a new test case YAML file.

    The file is written to ``benchmarks_dir/<language>/<id>.yaml``.

    Raises:
        DuplicateTestIdError: If a test with the same ID already exists.
    """
    benchmarks_path = Path(benchmarks_dir)
    _check_id_not_exists(benchmarks_path, test.id)

    lang_dir = benchmarks_path / test.language
    lang_dir.mkdir(parents=True, exist_ok=True)
    out_path = lang_dir / f"{test.id}.yaml"

    _write_test_yaml(out_path, test)
    logger.info("Test created: %s -> %s", test.id, out_path)
    return out_path


def update_test(benchmarks_dir: str, test_id: str, test: TestCase) -> Path:
    """Update an existing test case by finding and overwriting its YAML file.

    Raises:
        TestNotFoundError: If the original test_id is not found.
        DuplicateTestIdError: If renaming to an ID that already exists.
    """
    benchmarks_path = Path(benchmarks_dir)
    existing_path = _find_test_file(benchmarks_path, test_id)

    if test.id != test_id:
        _check_id_not_exists(benchmarks_path, test.id)

    _write_test_yaml(existing_path, test)
    logger.info("Test updated: %s", test_id)
    return existing_path


def delete_test(benchmarks_dir: str, test_id: str) -> None:
    """Delete a test case YAML file.

    Raises:
        TestNotFoundError: If no test with the given ID exists.
    """
    benchmarks_path = Path(benchmarks_dir)
    path = _find_test_file(benchmarks_path, test_id)
    path.unlink()
    logger.info("Test deleted: %s (%s)", test_id, path)


def _parse_test_case(data: dict) -> TestCase:
    """Parse a raw YAML dict into a TestCase dataclass."""
    return TestCase(
        id=data["id"],
        title=data["title"],
        language=data["language"],
        difficulty=data.get("difficulty", "unknown"),
        prompt=data["prompt"],
        code=data.get("code"),
        expected_issues=data.get("expected_issues", []),
        notes=data.get("notes"),
    )


def _find_test_file(benchmarks_path: Path, test_id: str) -> Path:
    """Locate the YAML file for a given test ID."""
    for yaml_file in benchmarks_path.rglob("*.yaml"):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        if data and data.get("id") == test_id:
            return yaml_file
    raise TestNotFoundError(f"Test case not found: {test_id}")


def _check_id_not_exists(benchmarks_path: Path, test_id: str) -> None:
    """Raise DuplicateTestIdError if the given test ID already exists."""
    for yaml_file in benchmarks_path.rglob("*.yaml"):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        if data and data.get("id") == test_id:
            raise DuplicateTestIdError(f"Test ID already exists: {test_id}")


def _write_test_yaml(path: Path, test: TestCase) -> None:
    """Serialize a TestCase to YAML and write it to disk."""
    data = {
        "id": test.id,
        "title": test.title,
        "language": test.language,
        "difficulty": test.difficulty,
        "prompt": test.prompt,
    }
    if test.code is not None:
        data["code"] = test.code
    if test.expected_issues:
        data["expected_issues"] = list(test.expected_issues)
    if test.notes is not None:
        data["notes"] = test.notes

    with open(path, "w") as f:
        yaml.dump(
            data, f, default_flow_style=False, sort_keys=False, allow_unicode=True
        )
