from __future__ import annotations

import argparse
from datetime import datetime, timezone

from .client import LLMClient
from .loader import load_tests
from .metrics import compute_tokens_per_second
from .models import RunMetadata, TestCase, TestResult
from .results import create_run_dir, get_next_run_id, save_metadata, save_result

DEFAULT_SYSTEM_PROMPT = (
    "You are a senior software engineer reviewing code for bugs. "
    "Focus on concurrency issues, error handling, and distributed systems correctness. "
    "Be specific: identify the exact lines, explain the bug, and describe the consequence."
)


def build_prompt(test: TestCase) -> str:
    if test.code:
        return f"{test.prompt}\n\n```{test.language}\n{test.code}```"
    return test.prompt


def run(args: argparse.Namespace) -> None:
    client = LLMClient(
        args.api_url,
        args.model,
        args.temperature,
        args.max_tokens,
        think=args.think,
        debug=args.debug,
    )
    tests = load_tests(args.tests_dir, tags=args.tags)

    if not tests:
        print("No test cases found. Check --tests-dir and --tags.")
        return

    run_id = get_next_run_id(args.results_dir, args.model)
    run_dir = create_run_dir(args.results_dir, args.model, run_id)
    system_prompt = args.system_prompt or DEFAULT_SYSTEM_PROMPT

    print(f"Model: {args.model}")
    print(f"Run:   {run_id}")
    print(f"Tests: {len(tests)}")
    print(f"Output: {run_dir}")
    print("-" * 60)

    results: list[TestResult] = []
    run_start = datetime.now(timezone.utc)

    for i, test in enumerate(tests, 1):
        print(f"[{i}/{len(tests)}] {test.id}: {test.title}")
        user_prompt = build_prompt(test)
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            print("  ", end="", flush=True)
            response, usage, elapsed = client.query(system_prompt, user_prompt)
            tps = compute_tokens_per_second(usage, elapsed)

            prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
            completion_tokens = (
                getattr(usage, "completion_tokens", None) if usage else None
            )
            total_tokens = getattr(usage, "total_tokens", None) if usage else None

            result = TestResult(
                test_id=test.id,
                model=args.model,
                prompt_sent=f"[SYSTEM] {system_prompt}\n\n[USER] {user_prompt}",
                response=response,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                elapsed_seconds=round(elapsed, 2),
                tokens_per_second=round(tps, 1) if tps else None,
                timestamp=timestamp,
            )

            tps_str = f" | {tps:.1f} tok/s" if tps else ""
            print(f"\n— {elapsed:.1f}s{tps_str}")

        except Exception as e:
            result = TestResult(
                test_id=test.id,
                model=args.model,
                prompt_sent=f"[SYSTEM] {system_prompt}\n\n[USER] {user_prompt}",
                response="",
                prompt_tokens=None,
                completion_tokens=None,
                total_tokens=None,
                elapsed_seconds=0,
                tokens_per_second=None,
                timestamp=timestamp,
                error=str(e),
            )
            print(f"— ERROR: {e}")

        save_result(run_dir, result)
        results.append(result)

    total_elapsed = sum(r.elapsed_seconds for r in results)
    tps_values = [r.tokens_per_second for r in results if r.tokens_per_second]
    avg_tps = sum(tps_values) / len(tps_values) if tps_values else None

    metadata = RunMetadata(
        run_id=run_id,
        model=args.model,
        api_url=args.api_url,
        timestamp=run_start.isoformat(),
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        total_tests=len(results),
        total_elapsed_seconds=round(total_elapsed, 2),
        avg_tokens_per_second=round(avg_tps, 1) if avg_tps else None,
        test_ids=[r.test_id for r in results],
    )
    save_metadata(run_dir, metadata)

    print("-" * 60)
    print(f"Done. {len(results)} tests in {total_elapsed:.1f}s")
    if avg_tps:
        print(f"Avg tokens/sec: {avg_tps:.1f}")
    print(f"Results: {run_dir}")
