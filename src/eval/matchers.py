"""Argument matching strategies for comparing expected vs actual tool calls."""

from __future__ import annotations

from src.models import MatchLevel

from rapidfuzz import fuzz


def match_value(expected, actual, level: MatchLevel) -> bool:
    """Compare a single expected value against an actual value."""
    if level == MatchLevel.EXACT:
        return _exact(expected, actual)
    elif level == MatchLevel.TYPE_ONLY:
        return _type_only(expected, actual)
    else:  # FUZZY
        return _fuzzy(expected, actual)


def _exact(expected, actual) -> bool:
    if isinstance(expected, str) and isinstance(actual, str):
        return expected.strip().lower() == actual.strip().lower()
    return expected == actual


def _fuzzy(expected, actual) -> bool:
    """Fuzzy matching — strings get token-set-ratio, numbers get tolerance."""
    if expected is None:
        return actual is None

    if isinstance(expected, str) and isinstance(actual, str):
        return fuzz.token_sort_ratio(expected.lower(), actual.lower()) >= 80

    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if expected == 0:
            return abs(actual) < 1e-6
        return abs(expected - actual) / abs(expected) < 0.01  # 1% tolerance

    if isinstance(expected, bool) and isinstance(actual, bool):
        return expected == actual

    if isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            return False
        return all(_fuzzy(e, a) for e, a in zip(expected, actual))

    if isinstance(expected, dict) and isinstance(actual, dict):
        if set(expected.keys()) != set(actual.keys()):
            return False
        return all(_fuzzy(expected[k], actual[k]) for k in expected)

    # Fall back to exact
    return expected == actual


def _type_only(expected, actual) -> bool:
    """Only checks that the types match, not values."""
    return type(expected) is type(actual)


def match_tool_call(
    expected: dict,
    actual: dict,
    level: MatchLevel,
) -> tuple[bool, dict[str, bool]]:
    """Compare one expected tool call against one actual tool call.

    Returns (name_correct, {arg_name: matched}).
    """
    name_correct = expected["name"] == actual.get("name", "")

    expected_args = expected.get("arguments", {})
    actual_args = actual.get("arguments", {})

    arg_scores: dict[str, bool] = {}
    for key, exp_val in expected_args.items():
        if key not in actual_args:
            arg_scores[key] = False
        else:
            arg_scores[key] = match_value(exp_val, actual_args[key], level)

    return name_correct, arg_scores


def find_hallucinated_args(expected: dict, actual: dict) -> list[str]:
    """Return argument names present in actual but not in expected schema."""
    expected_keys = set(expected.get("arguments", {}).keys())
    actual_keys = set(actual.get("arguments", {}).keys())
    return sorted(actual_keys - expected_keys)


def match_tool_calls(
    expected_calls: list[dict],
    actual_calls: list[dict],
    level: MatchLevel,
) -> tuple[
    list[tuple[dict, dict, bool, dict[str, bool]]],
    list[dict],
    list[dict],
]:
    """Match a list of expected tool calls against actual calls.

    Uses greedy best-match: for each expected call, find the actual call
    with the same function name and best argument match.  Each actual call
    can only be consumed once.

    Returns:
        matched: List of ``(expected, actual, name_correct, arg_scores)`` tuples.
        unmatched_expected: Expected calls with no matching actual call.
        unmatched_actual: Actual calls not consumed by any expected call.
    """
    remaining = list(range(len(actual_calls)))
    matched: list[tuple[dict, dict, bool, dict[str, bool]]] = []
    unmatched_expected: list[dict] = []

    for exp in expected_calls:
        best_idx: int | None = None
        best_score = -1.0
        best_name_ok = False
        best_arg_scores: dict[str, bool] = {}

        for i in remaining:
            act = actual_calls[i]
            name_ok, arg_scores = match_tool_call(exp, act, level)

            # Score: name match counts most, then fraction of correct args
            if arg_scores:
                arg_frac = sum(arg_scores.values()) / len(arg_scores)
            else:
                arg_frac = 1.0 if name_ok else 0.0

            score = (1.0 if name_ok else 0.0) + arg_frac

            if score > best_score:
                best_score = score
                best_idx = i
                best_name_ok = name_ok
                best_arg_scores = arg_scores

        if best_idx is not None and best_name_ok:
            matched.append(
                (exp, actual_calls[best_idx], best_name_ok, best_arg_scores)
            )
            remaining.remove(best_idx)
        else:
            unmatched_expected.append(exp)

    unmatched_actual = [actual_calls[i] for i in remaining]
    return matched, unmatched_expected, unmatched_actual
