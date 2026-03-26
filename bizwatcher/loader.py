from __future__ import annotations

from pathlib import Path

import yaml

from .models import TestCase


def load_tests(tests_dir: str, tags: list[str] | None = None) -> list[TestCase]:
    """Discover and load all YAML test cases from tests_dir, optionally filtered by tags."""
    tests_path = Path(tests_dir)
    if not tests_path.is_dir():
        raise FileNotFoundError(f"Tests directory not found: {tests_dir}")

    cases: list[TestCase] = []
    for yaml_file in sorted(tests_path.rglob("*.yaml")):
        with open(yaml_file) as f:
            data = yaml.safe_load(f)

        if not data:
            continue

        case = TestCase(
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

        if tags:
            if not set(tags) & set(case.tags):
                continue

        cases.append(case)

    cases.sort(key=lambda c: (c.language, c.id))
    return cases
