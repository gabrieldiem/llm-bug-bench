"""LLM-based judge that scores bug-detection responses on a 1-20 rubric."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import openai

from ..exceptions import JudgeParseError
from ..models import JudgeResult, RunProgress
from .loader import load_tests
from .results import load_all_results, load_judge_result, save_judge_result

logger = logging.getLogger(__name__)

DEFAULT_JUDGE_MODEL = "gpt-5.2-chat-latest"

JUDGE_SYSTEM_PROMPT = (
    "You are an expert software engineering evaluator assessing the quality of bug reports. "
    "Respond with valid JSON only — no markdown, no code blocks."
)

SCORING_RUBRIC = """
Score on a scale of 1–20:
- 17–20: All issues found with precise explanation of root cause and consequence
- 13–16: Most issues found, minor gaps or imprecise explanations
- 9–12: Some issues found, significant gaps in coverage or explanation
- 5–8: Few issues found, or explanations are vague and unhelpful
- 1–4: Issues missed, wrong analysis, or hallucinated bugs
"""


class JudgeClient:
    """Client for evaluating LLM responses using an OpenAI judge model."""

    def __init__(self, model: str, api_key: str):
        self._model = model
        self._client = openai.OpenAI(api_key=api_key)

    def evaluate(
        self,
        prompt_sent: str,
        response: str,
        expected_issues: list[str],
    ) -> tuple[dict, int | None, int | None, float]:
        """Score a single LLM response against expected issues.

        Returns:
            Tuple of (parsed_json, prompt_tokens, completion_tokens, elapsed_seconds).
        """
        user_prompt = _build_judge_prompt(prompt_sent, response, expected_issues)
        start = time.monotonic()
        completion = self._client.chat.completions.create(
            model=self._model,
            temperature=0.0,
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
        )
        elapsed = time.monotonic() - start

        raw = completion.choices[0].message.content or ""
        parsed = _parse_judge_response(raw)

        usage = completion.usage
        prompt_tokens = getattr(usage, "prompt_tokens", None) if usage else None
        completion_tokens = getattr(usage, "completion_tokens", None) if usage else None

        return parsed, prompt_tokens, completion_tokens, elapsed


def judge_run(
    run_dir: Path,
    benchmarks_dir: str,
    judge_model: str,
    api_key: str,
    task_id: str,
    progress_cb: Callable[[RunProgress], None] | None = None,
) -> list[JudgeResult]:
    """Judge all results in a run directory.

    Args:
        run_dir: Path to the run_NNN directory.
        benchmarks_dir: Path to YAML benchmark cases for expected_issues lookup.
        judge_model: OpenAI model name to use as judge.
        api_key: OpenAI API key.
        task_id: Background task identifier for progress tracking.
        progress_cb: Optional callback for SSE progress updates.

    Returns:
        List of JudgeResult for all tests in the run.
    """
    client = JudgeClient(model=judge_model, api_key=api_key)
    results = load_all_results(run_dir)

    if not results:
        logger.info("No test results found in %s", run_dir)
        return []

    tests = load_tests(benchmarks_dir)
    test_index = {t.id: t for t in tests}
    judge_results: list[JudgeResult] = []

    logger.info(
        "Judge started: run_dir=%s model=%s results=%d",
        run_dir,
        judge_model,
        len(results),
    )

    for i, result in enumerate(results, 1):
        existing = load_judge_result(run_dir, result.test_id)
        if existing is not None:
            logger.info(
                "[%d/%d] %s: skipped (already judged, score=%d)",
                i,
                len(results),
                result.test_id,
                existing.score,
            )
            judge_results.append(existing)
            continue

        test = test_index.get(result.test_id)
        expected_issues = test.expected_issues if test else []
        timestamp = datetime.now(timezone.utc).isoformat()

        if progress_cb:
            progress_cb(
                RunProgress(
                    run_id=run_dir.name,
                    task_id=task_id,
                    status="running",
                    current_test=i,
                    total_tests=len(results),
                    current_test_id=result.test_id,
                    elapsed_seconds=0,
                    message=f"Judging {result.test_id}",
                )
            )

        try:
            parsed, prompt_tokens, completion_tokens, elapsed = client.evaluate(
                result.prompt_sent, result.response, expected_issues
            )
            score = int(parsed.get("score", 1))
            jr = JudgeResult(
                test_id=result.test_id,
                judge_model=judge_model,
                score=score,
                explanation=parsed.get("explanation", ""),
                issues_found=parsed.get("issues_found", []),
                issues_expected=expected_issues,
                issues_matched=parsed.get("issues_matched", []),
                issues_missed=parsed.get("issues_missed", []),
                timestamp=timestamp,
                judge_prompt_tokens=prompt_tokens,
                judge_completion_tokens=completion_tokens,
                judge_elapsed_seconds=round(elapsed, 2),
            )
            logger.info(
                "[%d/%d] %s: score=%d (%.1fs)",
                i,
                len(results),
                result.test_id,
                score,
                elapsed,
            )
        except Exception as e:
            jr = JudgeResult(
                test_id=result.test_id,
                judge_model=judge_model,
                score=1,
                explanation="",
                issues_found=[],
                issues_expected=expected_issues,
                issues_matched=[],
                issues_missed=expected_issues,
                timestamp=timestamp,
                judge_prompt_tokens=None,
                judge_completion_tokens=None,
                judge_elapsed_seconds=0.0,
                error=str(e),
            )
            logger.warning(
                "[%d/%d] %s: judge error: %s", i, len(results), result.test_id, e
            )

        save_judge_result(run_dir, jr)
        judge_results.append(jr)

    scores = [jr.score for jr in judge_results]
    avg_score = sum(scores) / len(scores) if scores else 0
    logger.info("Judge completed: avg_score=%.1f", avg_score)

    if progress_cb:
        progress_cb(
            RunProgress(
                run_id=run_dir.name,
                task_id=task_id,
                status="completed",
                current_test=len(results),
                total_tests=len(results),
                current_test_id=results[-1].test_id if results else "",
                elapsed_seconds=0,
                message=f"Judging complete. Avg score: {avg_score:.1f}",
            )
        )

    return judge_results


def _build_judge_prompt(
    prompt_sent: str, response: str, expected_issues: list[str]
) -> str:
    """Construct the evaluation prompt for the judge model."""
    numbered = "\n".join(f"{i + 1}. {issue}" for i, issue in enumerate(expected_issues))
    return f"""You are evaluating a bug-detection response from an LLM.

## Original Prompt Sent to LLM
{prompt_sent}

## LLM Response
{response}

## Expected Issues (ground truth)
{numbered}

{SCORING_RUBRIC}

Respond with a JSON object with these fields:
- "score": integer 1–20
- "explanation": string summarizing the quality of the response
- "issues_found": list of strings describing bugs the LLM identified (your extraction)
- "issues_matched": list of strings from expected issues that the LLM addressed correctly
- "issues_missed": list of strings from expected issues that the LLM missed or got wrong
"""


def _parse_judge_response(raw: str) -> dict:
    """Parse the judge's JSON response, stripping markdown code blocks if present."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise JudgeParseError(
            f"Failed to parse judge response as JSON: {e}\nRaw: {raw}"
        ) from e
