"""Evaluation runner — drives test cases through a runtime and scores results."""

from __future__ import annotations

import logging
from typing import Sequence

from rich.progress import Progress, SpinnerColumn, TextColumn

from src.models import EvalResult, MatchLevel, TestCase, ToolCallResult
from src.eval.matchers import find_hallucinated_args, match_tool_call, match_tool_calls
from src.runtimes.base import BaseRuntime

logger = logging.getLogger(__name__)


def run_evaluation(
    runtime: BaseRuntime,
    test_cases: Sequence[TestCase],
    *,
    num_runs: int = 1,
    warmup: bool = True,
    show_progress: bool = True,
) -> list[EvalResult]:
    """Execute *test_cases* against *runtime* and return scored results.

    Args:
        runtime: A configured runtime backend.
        test_cases: The test suite to evaluate.
        num_runs: Repeat each test this many times (useful for variance).
        warmup: If True, send a throwaway request first to avoid cold-start.
        show_progress: Show a progress bar.
    """
    if warmup:
        runtime.warmup()

    results: list[EvalResult] = []

    if show_progress:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            task = progress.add_task("Evaluating…", total=len(test_cases) * num_runs)
            for tc in test_cases:
                for _ in range(num_runs):
                    r = _evaluate_single(runtime, tc)
                    results.append(r)
                    progress.advance(task)
    else:
        for tc in test_cases:
            for _ in range(num_runs):
                results.append(_evaluate_single(runtime, tc))

    return results


def _evaluate_single(runtime: BaseRuntime, tc: TestCase) -> EvalResult:
    """Run one test case and score the result."""
    result = EvalResult(
        test_id=tc.id,
        category=tc.category,
        runtime_name=runtime.config.name,
        model_id=runtime.config.model_id,
        expected_negative=tc.is_negative,
    )

    # ---- call the model --------------------------------------------------
    try:
        api_result: ToolCallResult = runtime.chat_with_tools(
            messages=tc.messages,
            tools=tc.tools,
            temperature=0.0,
        )
    except Exception as exc:
        result.error = str(exc)
        logger.warning("Error on test %s: %s", tc.id, exc)
        return result

    result.latency_ms = api_result.timing.get("total_ms", 0.0)
    result.tokens_per_sec = api_result.timing.get("tokens_per_sec", 0.0)
    result.prompt_tokens = api_result.usage.get("prompt_tokens", 0)
    result.completion_tokens = api_result.usage.get("completion_tokens", 0)
    result.raw_response = api_result.raw_response

    actual_calls = api_result.tool_calls

    # ---- negative tests (should NOT call any tool) -----------------------
    if tc.is_negative:
        result.correctly_refused = len(actual_calls) == 0
        result.full_match = result.correctly_refused
        result.tool_name_correct = result.correctly_refused
        return result

    # ---- positive tests --------------------------------------------------
    if not tc.expected_tool_calls:
        # No expected calls defined — can't score accuracy
        result.full_match = False
        return result

    if not actual_calls:
        # Model produced no tool calls but we expected some
        result.tool_name_correct = False
        result.full_match = False
        return result

    # Match expected tool calls against actual calls (supports multi-tool)
    matched, unmatched_expected, unmatched_actual = match_tool_calls(
        tc.expected_tool_calls, actual_calls, tc.match_level,
    )

    # Aggregate per-pair scores
    all_names_ok = True
    merged_arg_scores: dict[str, bool] = {}
    all_hallucinated: list[str] = []

    for exp, act, name_ok, arg_scores in matched:
        if not name_ok:
            all_names_ok = False
        halluc = find_hallucinated_args(exp, act)
        all_hallucinated.extend(halluc)
        # Prefix arg keys with tool name to avoid collisions
        prefix = exp["name"]
        for k, v in arg_scores.items():
            merged_arg_scores[f"{prefix}.{k}"] = v

    # Unmatched expected calls count as failures
    if unmatched_expected:
        all_names_ok = False
        for exp in unmatched_expected:
            for k in exp.get("arguments", {}):
                merged_arg_scores[f"{exp['name']}.{k}"] = False

    # Unmatched actual calls are hallucinated tools
    has_hallucinated_tools = len(unmatched_actual) > 0

    result.tool_name_correct = all_names_ok and not unmatched_expected
    result.argument_scores = merged_arg_scores
    result.full_match = (
        all_names_ok
        and not unmatched_expected
        and not unmatched_actual
        and all(merged_arg_scores.values())
    )
    result.hallucinated_tools = has_hallucinated_tools
    result.hallucinated_args = all_hallucinated

    return result
