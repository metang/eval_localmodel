"""Rich console reporting for evaluation results."""

from __future__ import annotations

from rich.console import Console
from rich.table import Table

from src.eval.results import RunSummary, results_to_dataframe
from src.models import EvalResult


console = Console()


def print_summary(summary: RunSummary) -> None:
    """Print a rich summary table to the console."""
    console.print()
    console.rule(
        f"[bold]{summary.runtime_name} / {summary.model_id}[/bold]",
        style="cyan",
    )

    # ---- overall stats ---------------------------------------------------
    table = Table(title="Overall", show_header=True, header_style="bold green")
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right")

    table.add_row("Total test cases", str(summary.total_cases))
    table.add_row(
        "Full match rate", f"{summary.overall_full_match_rate:.1%}"
    )
    table.add_row(
        "Tool selection rate", f"{summary.overall_tool_selection_rate:.1%}"
    )
    table.add_row(
        "Argument accuracy", f"{summary.overall_arg_accuracy:.1%}"
    )
    table.add_row("Avg latency (ms)", f"{summary.avg_latency_ms:.0f}")
    table.add_row("Avg tokens/sec", f"{summary.avg_tokens_per_sec:.1f}")
    console.print(table)

    # ---- per-category breakdown ------------------------------------------
    cat_table = Table(
        title="By Category", show_header=True, header_style="bold magenta"
    )
    cat_table.add_column("Category")
    cat_table.add_column("N", justify="right")
    cat_table.add_column("Full Match", justify="right")
    cat_table.add_column("Tool Select", justify="right")
    cat_table.add_column("Arg Acc", justify="right")
    cat_table.add_column("Latency (ms)", justify="right")
    cat_table.add_column("Tok/s", justify="right")
    cat_table.add_column("Errors", justify="right")

    for cs in summary.categories:
        cat_table.add_row(
            cs.category,
            str(cs.total),
            f"{cs.full_match_rate:.0%}",
            f"{cs.tool_selection_rate:.0%}",
            f"{cs.avg_arg_accuracy:.0%}",
            f"{cs.avg_latency_ms:.0f}",
            f"{cs.avg_tokens_per_sec:.1f}",
            str(cs.errors),
        )

    console.print(cat_table)
    console.print()


def print_failures(results: list[EvalResult]) -> None:
    """Print details for every test case that did not fully match."""
    failures = [r for r in results if not r.full_match and not r.error]
    if not failures:
        console.print("[green]All tests passed![/green]")
        return

    console.rule("[bold red]Failures[/bold red]")
    for r in failures:
        console.print(
            f"  [red]✗[/red] {r.test_id} — "
            f"name={'✓' if r.tool_name_correct else '✗'} "
            f"args={r.argument_accuracy:.0%} "
            f"halluc_args={r.hallucinated_args}"
        )


def print_comparison(summaries: list[RunSummary]) -> None:
    """Side-by-side comparison table of multiple runs."""
    table = Table(title="Comparison", show_header=True, header_style="bold yellow")
    table.add_column("Runtime / Model")
    table.add_column("Full Match", justify="right")
    table.add_column("Tool Select", justify="right")
    table.add_column("Arg Acc", justify="right")
    table.add_column("Latency (ms)", justify="right")
    table.add_column("Tok/s", justify="right")

    for s in summaries:
        table.add_row(
            f"{s.runtime_name}/{s.model_id}",
            f"{s.overall_full_match_rate:.1%}",
            f"{s.overall_tool_selection_rate:.1%}",
            f"{s.overall_arg_accuracy:.1%}",
            f"{s.avg_latency_ms:.0f}",
            f"{s.avg_tokens_per_sec:.1f}",
        )

    console.print(table)


def export_csv(results: list[EvalResult], path: str) -> None:
    """Export results to a CSV file."""
    df = results_to_dataframe(results)
    df.to_csv(path, index=False)
    console.print(f"[green]Results exported to {path}[/green]")
