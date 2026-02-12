"""Aggregate EvalResult lists into summary tables and statistics."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import pandas as pd

from src.models import EvalResult


@dataclass
class CategorySummary:
    category: str
    total: int = 0
    tool_name_correct: int = 0
    full_match: int = 0
    avg_arg_accuracy: float = 0.0
    avg_latency_ms: float = 0.0
    avg_tokens_per_sec: float = 0.0
    errors: int = 0

    @property
    def tool_selection_rate(self) -> float:
        return self.tool_name_correct / self.total if self.total else 0.0

    @property
    def full_match_rate(self) -> float:
        return self.full_match / self.total if self.total else 0.0


@dataclass
class RunSummary:
    runtime_name: str
    model_id: str
    total_cases: int = 0
    overall_full_match_rate: float = 0.0
    overall_tool_selection_rate: float = 0.0
    overall_arg_accuracy: float = 0.0
    avg_latency_ms: float = 0.0
    avg_tokens_per_sec: float = 0.0
    categories: list[CategorySummary] = field(default_factory=list)


def summarize(results: list[EvalResult]) -> RunSummary:
    """Build a RunSummary from a flat list of eval results."""
    if not results:
        return RunSummary(runtime_name="", model_id="")

    runtime_name = results[0].runtime_name
    model_id = results[0].model_id

    by_cat: dict[str, list[EvalResult]] = defaultdict(list)
    for r in results:
        by_cat[r.category].append(r)

    cat_summaries: list[CategorySummary] = []
    for cat, cat_results in sorted(by_cat.items()):
        cs = _summarize_category(cat, cat_results)
        cat_summaries.append(cs)

    total = len(results)
    full_match_total = sum(cs.full_match for cs in cat_summaries)
    tool_name_total = sum(cs.tool_name_correct for cs in cat_summaries)

    arg_accs = [r.argument_accuracy for r in results if not r.error]
    latencies = [r.latency_ms for r in results if r.latency_ms > 0]
    tps_vals = [r.tokens_per_sec for r in results if r.tokens_per_sec > 0]

    return RunSummary(
        runtime_name=runtime_name,
        model_id=model_id,
        total_cases=total,
        overall_full_match_rate=full_match_total / total if total else 0.0,
        overall_tool_selection_rate=tool_name_total / total if total else 0.0,
        overall_arg_accuracy=sum(arg_accs) / len(arg_accs) if arg_accs else 0.0,
        avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0.0,
        avg_tokens_per_sec=sum(tps_vals) / len(tps_vals) if tps_vals else 0.0,
        categories=cat_summaries,
    )


def results_to_dataframe(results: list[EvalResult]) -> pd.DataFrame:
    """Convert results to a DataFrame for further analysis."""
    rows = []
    for r in results:
        rows.append(
            {
                "test_id": r.test_id,
                "category": r.category,
                "runtime": r.runtime_name,
                "model": r.model_id,
                "tool_name_correct": r.tool_name_correct,
                "argument_accuracy": r.argument_accuracy,
                "full_match": r.full_match,
                "hallucinated_tools": r.hallucinated_tools,
                "hallucinated_args": len(r.hallucinated_args),
                "latency_ms": r.latency_ms,
                "tokens_per_sec": r.tokens_per_sec,
                "prompt_tokens": r.prompt_tokens,
                "completion_tokens": r.completion_tokens,
                "error": r.error,
            }
        )
    return pd.DataFrame(rows)


# ---- internal ------------------------------------------------------------


def _summarize_category(cat: str, results: list[EvalResult]) -> CategorySummary:
    total = len(results)
    tool_ok = sum(1 for r in results if r.tool_name_correct)
    full_ok = sum(1 for r in results if r.full_match)
    errors = sum(1 for r in results if r.error)

    arg_accs = [r.argument_accuracy for r in results if not r.error]
    latencies = [r.latency_ms for r in results if r.latency_ms > 0]
    tps = [r.tokens_per_sec for r in results if r.tokens_per_sec > 0]

    return CategorySummary(
        category=cat,
        total=total,
        tool_name_correct=tool_ok,
        full_match=full_ok,
        avg_arg_accuracy=sum(arg_accs) / len(arg_accs) if arg_accs else 0.0,
        avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0.0,
        avg_tokens_per_sec=sum(tps) / len(tps) if tps else 0.0,
        errors=errors,
    )
