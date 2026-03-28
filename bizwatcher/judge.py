from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone

import openai

from .loader import load_tests
from .models import JudgeResult
from .results import load_all_results, load_judge_result, save_judge_result

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


class JudgeParseError(ValueError):
    pass


class JudgeClient:
    def __init__(self, model: str, api_key: str):
        self._model = model
        self._client = openai.OpenAI(api_key=api_key)

    def evaluate(
        self,
        prompt_sent: str,
        response: str,
        expected_issues: list[str],
    ) -> tuple[dict, int | None, int | None, float]:
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


def _build_judge_prompt(
    prompt_sent: str, response: str, expected_issues: list[str]
) -> str:
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
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise JudgeParseError(
            f"Failed to parse judge response as JSON: {e}\nRaw: {raw}"
        )


def judge(args: argparse.Namespace) -> None:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY environment variable is not set")

    judge_model = getattr(args, "judge_model", DEFAULT_JUDGE_MODEL)
    client = JudgeClient(model=judge_model, api_key=api_key)

    from pathlib import Path

    run_dir = Path(args.run_dir)
    results = load_all_results(run_dir)

    if not results:
        print("No test results found in run directory.")
        return

    tests = load_tests(args.tests_dir)
    test_index = {t.id: t for t in tests}

    print(f"Judge model: {judge_model}")
    print(f"Run dir:     {run_dir}")
    print(f"Results:     {len(results)}")
    print("-" * 60)

    scores: list[int] = []

    for i, result in enumerate(results, 1):
        existing = load_judge_result(run_dir, result.test_id)
        if existing is not None:
            print(
                f"[{i}/{len(results)}] {result.test_id}: SKIP (already judged, score={existing.score})"
            )
            scores.append(existing.score)
            continue

        test = test_index.get(result.test_id)
        expected_issues = test.expected_issues if test else []

        print(f"[{i}/{len(results)}] {result.test_id}: judging...", end=" ", flush=True)
        timestamp = datetime.now(timezone.utc).isoformat()

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
            print(f"score={score} ({elapsed:.1f}s)")
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
            print(f"ERROR: {e}")

        save_judge_result(run_dir, jr)
        scores.append(jr.score)

    print("-" * 60)
    if scores:
        print(
            f"Scores — min={min(scores)}  max={max(scores)}  avg={sum(scores)/len(scores):.1f}"
        )
