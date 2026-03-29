"""Core benchmark runner — loads tests, queries LLMs, saves results."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timezone

from ..metrics import compute_tokens_per_second
from ..models import RunConfig, RunMetadata, RunProgress, TestCase, TestResult
from .llm_client import create_client_from_config
from .loader import load_tests
from .results import create_run_dir, get_next_run_id, save_metadata, save_result

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = (
    "You are a code review expert specializing in concurrency, error handling, "
    "and distributed systems. Your task is to find bugs in the provided code or "
    "answer the given question.\n\n"
    "For code reviews, follow this structure:\n"
    "1. List each bug you find with:\n"
    "   - The exact line(s) where the bug occurs\n"
    "   - What the bug is (root cause)\n"
    "   - What happens at runtime (consequence)\n"
    "   - How to fix it\n"
    "2. Only report real bugs — do not invent issues that are not present.\n"
    "3. Consider language-specific semantics (e.g., GIL in Python, goroutine "
    "scheduling in Go).\n\n"
    "For theory questions, give a precise and structured answer.\n\n"
    "Be thorough but concise. Do not repeat the code back."
)


def build_prompt(test: TestCase) -> str:
    """Build the user prompt from a test case, appending code if present."""
    if test.code:
        return f"{test.prompt}\n\n```{test.language}\n{test.code}```"
    return test.prompt


def run_with_config(
    config: RunConfig,
    task_id: str,
    progress_cb: Callable[[RunProgress], None] | None = None,
) -> RunMetadata:
    """Execute a benchmark run. Calls progress_cb after each test.

    Args:
        config: Full run configuration including provider, model, and params.
        task_id: Unique identifier for background task tracking.
        progress_cb: Optional callback for SSE progress updates.

    Returns:
        RunMetadata with aggregate stats for the completed run.
    """
    client = create_client_from_config(
        config.provider_config,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        think=config.think,
    )
    tests = load_tests(config.tests_dir)

    if not tests:
        raise ValueError("No test cases found. Check tests_dir.")

    model = config.provider_config.model
    run_id = get_next_run_id(config.results_dir, model)
    run_dir = create_run_dir(config.results_dir, model, run_id)
    system_prompt = config.system_prompt or DEFAULT_SYSTEM_PROMPT

    logger.info(
        "Run started: model=%s run_id=%s tests=%d provider=%s",
        model,
        run_id,
        len(tests),
        config.provider_config.provider,
    )

    results: list[TestResult] = []
    run_start = datetime.now(timezone.utc)

    for i, test in enumerate(tests, 1):
        timestamp = datetime.now(timezone.utc).isoformat()

        if progress_cb:
            progress_cb(
                RunProgress(
                    run_id=run_id,
                    task_id=task_id,
                    status="running",
                    current_test=i,
                    total_tests=len(tests),
                    current_test_id=test.id,
                    elapsed_seconds=0,
                    message=f"Running {test.id}: {test.title}",
                )
            )

        logger.info("[%d/%d] %s: %s", i, len(tests), test.id, test.title)

        try:
            user_prompt = build_prompt(test)
            logger.debug(
                "Prompt length: system=%d user=%d", len(system_prompt), len(user_prompt)
            )
            response, usage, elapsed = client.query(system_prompt, user_prompt)
            tps = compute_tokens_per_second(usage, elapsed)

            prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
            completion_tokens = (
                getattr(usage, "completion_tokens", None) if usage else None
            )
            total_tokens = getattr(usage, "total_tokens", None) if usage else None

            result = TestResult(
                test_id=test.id,
                model=model,
                prompt_sent=f"[SYSTEM] {system_prompt}\n\n[USER] {user_prompt}",
                response=response,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                elapsed_seconds=round(elapsed, 2),
                tokens_per_second=round(tps, 1) if tps else None,
                timestamp=timestamp,
            )

            tps_str = f" {tps:.1f} tok/s" if tps else ""
            logger.info("%s completed: %.1fs%s", test.id, elapsed, tps_str)

        except Exception as e:
            result = TestResult(
                test_id=test.id,
                model=model,
                prompt_sent=f"[SYSTEM] {system_prompt}\n\n[USER] {build_prompt(test)}",
                response="",
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                elapsed_seconds=0,
                tokens_per_second=None,
                timestamp=timestamp,
                error=str(e),
            )
            logger.warning("%s failed: %s", test.id, e)

        save_result(run_dir, result)
        results.append(result)

    total_elapsed = sum(r.elapsed_seconds for r in results)
    tps_values = [r.tokens_per_second for r in results if r.tokens_per_second]
    avg_tps = sum(tps_values) / len(tps_values) if tps_values else None

    metadata = RunMetadata(
        run_id=run_id,
        model=model,
        api_url=config.provider_config.api_url,
        timestamp=run_start.isoformat(),
        temperature=config.temperature,
        max_tokens=config.max_tokens,
        total_tests=len(results),
        total_elapsed_seconds=round(total_elapsed, 2),
        avg_tokens_per_second=round(avg_tps, 1) if avg_tps else None,
        test_ids=[r.test_id for r in results],
        provider=config.provider_config.provider,
        system_prompt=system_prompt,
        think=config.think,
    )
    save_metadata(run_dir, metadata)

    logger.info(
        "Run completed: %d tests in %.1fs, avg_tps=%s, output=%s",
        len(results),
        total_elapsed,
        avg_tps,
        run_dir,
    )

    if progress_cb:
        progress_cb(
            RunProgress(
                run_id=run_id,
                task_id=task_id,
                status="completed",
                current_test=len(tests),
                total_tests=len(tests),
                current_test_id=tests[-1].id,
                elapsed_seconds=total_elapsed,
                message=f"Completed {len(results)} tests in {total_elapsed:.1f}s",
            )
        )

    return metadata
