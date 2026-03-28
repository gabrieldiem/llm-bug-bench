from __future__ import annotations

from pathlib import Path

import yaml

from ..exceptions import DuplicateTestIdError, TestNotFoundError
from ..models import TestCase


def load_tests(tests_dir: str, tags: list[str] | None = None) -> list[TestCase]:
    """Discover and load all YAML test cases, optionally filtered by tags."""
    tests_path = Path(tests_dir)
    if not tests_path.is_dir():
        raise FileNotFoundError(f"Tests directory not found: {tests_dir}")

    cases: list[TestCase] = []
    for yaml_file in sorted(tests_path.rglob("*.yaml")):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        if not data:
            continue

        case = _parse_test_case(data)

        if tags and not set(tags) & set(case.tags):
            continue

        cases.append(case)

    cases.sort(key=lambda c: (c.language, c.id))
    return cases


def load_test_by_id(tests_dir: str, test_id: str) -> TestCase:
    """Load a single test case by its ID."""
    tests_path = Path(tests_dir)
    for yaml_file in tests_path.rglob("*.yaml"):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        if data and data.get("id") == test_id:
            return _parse_test_case(data)
    raise TestNotFoundError(f"Test case not found: {test_id}")


def save_test(tests_dir: str, test: TestCase) -> Path:
    """Create a new test case YAML file. Raises if ID already exists."""
    tests_path = Path(tests_dir)
    _check_id_not_exists(tests_path, test.id)

    lang_dir = tests_path / test.language
    lang_dir.mkdir(parents=True, exist_ok=True)
    out_path = lang_dir / f"{test.id}.yaml"

    _write_test_yaml(out_path, test)
    return out_path


def update_test(tests_dir: str, test_id: str, test: TestCase) -> Path:
    """Update an existing test case. Finds and overwrites the YAML file."""
    tests_path = Path(tests_dir)
    existing_path = _find_test_file(tests_path, test_id)

    if test.id != test_id:
        _check_id_not_exists(tests_path, test.id)

    _write_test_yaml(existing_path, test)
    return existing_path


def delete_test(tests_dir: str, test_id: str) -> None:
    """Delete a test case YAML file."""
    tests_path = Path(tests_dir)
    path = _find_test_file(tests_path, test_id)
    path.unlink()


def get_all_tags(tests_dir: str) -> list[str]:
    """Return sorted list of all unique tags across test cases."""
    tests = load_tests(tests_dir)
    tags: set[str] = set()
    for t in tests:
        tags.update(t.tags)
    return sorted(tags)


def _parse_test_case(data: dict) -> TestCase:
    return TestCase(
        id=data["id"],
        title=data["title"],
        language=data["language"],
        tags=data.get("tags", []),
        difficulty=data.get("difficulty", "unknown"),
        prompt=data["prompt"],
        code=data.get("code"),
        expected_issues=data.get("expected_issues", []),
        notes=data.get("notes"),
    )


def _find_test_file(tests_path: Path, test_id: str) -> Path:
    for yaml_file in tests_path.rglob("*.yaml"):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        if data and data.get("id") == test_id:
            return yaml_file
    raise TestNotFoundError(f"Test case not found: {test_id}")


def _check_id_not_exists(tests_path: Path, test_id: str) -> None:
    for yaml_file in tests_path.rglob("*.yaml"):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)
        if data and data.get("id") == test_id:
            raise DuplicateTestIdError(f"Test ID already exists: {test_id}")


def _write_test_yaml(path: Path, test: TestCase) -> None:
    data = {
        "id": test.id,
        "title": test.title,
        "language": test.language,
        "tags": list(test.tags),
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
