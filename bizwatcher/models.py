from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TestCase:
    id: str
    title: str
    language: str
    tags: list[str]
    difficulty: str
    prompt: str
    code: str | None = None
    expected_issues: list[str] = field(default_factory=list)
    notes: str | None = None


@dataclass
class TestResult:
    test_id: str
    model: str
    prompt_sent: str
    response: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    elapsed_seconds: float
    tokens_per_second: float | None
    timestamp: str
    error: str | None = None


@dataclass
class RunMetadata:
    run_id: str
    model: str
    api_url: str
    timestamp: str
    temperature: float
    max_tokens: int
    total_tests: int
    total_elapsed_seconds: float
    avg_tokens_per_second: float | None
    test_ids: list[str] = field(default_factory=list)
