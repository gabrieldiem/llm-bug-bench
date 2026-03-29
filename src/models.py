"""Data models — frozen dataclasses for test cases, results, and configuration."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class TestCase:
    """A single bug-detection test case loaded from YAML."""

    id: str
    title: str
    language: str
    difficulty: str
    prompt: str
    code: str | None = None
    expected_issues: list[str] = field(default_factory=list)
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class TestResult:
    """Result of running a single test case against an LLM."""

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


@dataclass(frozen=True, slots=True)
class RunMetadata:
    """Aggregate metadata for a complete benchmark run."""

    run_id: str
    model: str
    api_url: str
    timestamp: str
    temperature: float
    total_tests: int
    total_elapsed_seconds: float
    avg_tokens_per_second: float | None
    test_ids: list[str] = field(default_factory=list)
    provider: str = "ollama"
    system_prompt: str = ""
    think: bool = False


@dataclass(frozen=True, slots=True)
class JudgeResult:
    """Evaluation of a single test result by the LLM judge."""

    test_id: str
    judge_model: str
    score: int
    explanation: str
    issues_found: list[str]
    issues_expected: list[str]
    issues_matched: list[str]
    issues_missed: list[str]
    timestamp: str
    judge_prompt_tokens: int | None
    judge_completion_tokens: int | None
    judge_elapsed_seconds: float
    error: str | None = None


@dataclass(frozen=True, slots=True)
class OllamaModel:
    """An LLM model available in a local Ollama instance."""

    name: str
    size: int
    parameter_size: str
    quantization: str
    modified_at: str
    family: str = ""


@dataclass(frozen=True, slots=True)
class LlamaCppModelInfo:
    """Status of a single model on a llama.cpp server."""

    name: str
    status: str  # e.g. "loaded", "unloaded"


@dataclass(frozen=True, slots=True)
class LlamaCppServerInfo:
    """Runtime information from a llama.cpp server instance."""

    server_url: str
    health_status: str
    models: list[LlamaCppModelInfo]
    total_slots: int
    idle_slots: int


@dataclass(frozen=True, slots=True)
class ProviderConfig:
    """Connection details for an LLM provider (Ollama, OpenAI, Gemini, or llama.cpp)."""

    provider: str
    api_url: str
    api_key: str
    model: str


@dataclass(frozen=True, slots=True)
class RunConfig:
    """All parameters needed to start a benchmark run."""

    provider_config: ProviderConfig
    temperature: float = 0.1
    system_prompt: str = ""
    think: bool = False
    benchmarks_dir: str = "./benchmarks"
    results_dir: str = "./results"


@dataclass(frozen=True, slots=True)
class RunProgress:
    """Progress update emitted during a benchmark run for SSE streaming."""

    run_id: str
    task_id: str
    status: str
    current_test: int
    total_tests: int
    current_test_id: str
    elapsed_seconds: float
    message: str = ""
    error: str | None = None
    batch_current: int | None = None
    batch_total: int | None = None
    batch_model: str | None = None


@dataclass(frozen=True, slots=True)
class LeaderboardEntry:
    """Aggregated benchmark data for one model across all its runs."""

    model: str
    provider: str
    parameter_size: str
    best_avg_score: float | None
    latest_avg_score: float | None
    avg_tokens_per_second: float | None
    total_runs: int
    best_run_id: str
