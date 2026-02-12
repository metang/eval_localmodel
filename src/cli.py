"""CLI entry point for eval-localmodel."""

from __future__ import annotations

import logging
import sys

import click
import yaml

from src.eval.results import summarize
from src.eval.runner import run_evaluation
from src.reporting.console import (
    console,
    export_csv,
    print_comparison,
    print_failures,
    print_summary,
)
from src.reporting.html import generate_html_report
from src.runtimes.base import RuntimeConfig
from src.runtimes.registry import create_runtime, list_runtimes
from src.test_suites import list_suites, load_all_suites, load_suites


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def main(verbose: bool) -> None:
    """eval-localmodel — evaluate local LLMs on tool-calling tasks."""
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(name)s %(levelname)s: %(message)s")


@main.command()
def runtimes() -> None:
    """List available runtime backends."""
    for name in list_runtimes():
        console.print(f"  • {name}")


@main.command()
def suites() -> None:
    """List available test suites."""
    for name in list_suites():
        console.print(f"  • {name}")


@main.command()
@click.option(
    "--runtime",
    "-r",
    required=True,
    help="Runtime backend to use (see 'runtimes' command for list)",
)
@click.option("--model", "-m", required=True, help="Model ID to evaluate")
@click.option(
    "--suite",
    "-s",
    multiple=True,
    help="Test suite name(s). Omit to run all.",
)
@click.option("--base-url", default=None, help="Override the runtime's base URL")
@click.option("--device", default=None, type=click.Choice(["cpu", "gpu", "npu"], case_sensitive=False), help="Device type for foundry-local (cpu/gpu/npu)")
@click.option("--runs", "-n", default=1, help="Repeat each test N times")
@click.option("--csv", "csv_path", default=None, help="Export results to CSV")
@click.option("--failures/--no-failures", default=True, help="Show failure details")
def run(
    runtime: str,
    model: str,
    suite: tuple[str, ...],
    base_url: str | None,
    device: str | None,
    runs: int,
    csv_path: str | None,
    failures: bool,
) -> None:
    """Run an evaluation."""
    # Validate runtime name
    available = list_runtimes()
    if runtime not in available:
        console.print(
            f"[red]Unknown runtime: {runtime!r}. "
            f"Available: {', '.join(available)}[/red]"
        )
        sys.exit(1)

    # Instantiate runtime
    try:
        if runtime == "foundry-local" and not base_url:
            # Use alias mode — SDK auto-discovers endpoint & model ID
            rt = create_runtime(runtime, alias=model, device=device)
        else:
            config = RuntimeConfig(name=runtime, model_id=model)
            if base_url:
                config.base_url = base_url
            rt = create_runtime(runtime, config=config)
    except Exception as exc:
        console.print(f"[red]Failed to create runtime: {exc}[/red]")
        sys.exit(1)

    if not rt.health_check():
        console.print(f"[red]Runtime {runtime} is not reachable. Is it running?[/red]")
        sys.exit(1)

    # Load tests
    test_cases = load_suites(suite) if suite else load_all_suites()
    console.print(f"Loaded [bold]{len(test_cases)}[/bold] test cases")

    # Run
    results = run_evaluation(rt, test_cases, num_runs=runs)

    # Report
    summary = summarize(results)
    print_summary(summary)

    if failures:
        print_failures(results)

    if csv_path:
        export_csv(results, csv_path)


@main.command()
@click.option(
    "--config",
    "-c",
    "config_path",
    required=True,
    type=click.Path(exists=True),
    help="YAML config file with multiple runtime/model combos",
)
@click.option("--suite", "-s", multiple=True)
@click.option("--csv", "csv_path", default=None)
@click.option("--html", "html_path", default=None, help="Export report to HTML file")
def compare(config_path: str, suite: tuple[str, ...], csv_path: str | None, html_path: str | None) -> None:
    """Compare multiple models/runtimes side-by-side.

    Config YAML format::

        runs:
          - runtime: ollama
            model: llama3.1
          - runtime: ollama
            model: qwen2.5:7b
          - runtime: foundry-local
            model: phi-4-mini
    """
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    test_cases = load_suites(suite) if suite else load_all_suites()

    all_results = []
    summaries = []
    entries = cfg["runs"]
    total_runs = len(entries)

    for idx, entry in enumerate(entries, 1):
        rt_name = entry["runtime"]
        model_id = entry["model"]
        base_url = entry.get("base_url")
        device = entry.get("device")

        label = f"{rt_name}/{model_id}"
        if device:
            label += f" [{device.upper()}]"

        console.rule(f"[bold]Run {idx}/{total_runs}: {label}[/bold]")

        try:
            if rt_name == "foundry-local" and not base_url:
                rt = create_runtime(rt_name, alias=model_id, device=device)
            else:
                rc = RuntimeConfig(name=rt_name, model_id=model_id)
                if base_url:
                    rc.base_url = base_url
                rt = create_runtime(rt_name, config=rc)
        except Exception as exc:
            console.print(f"[yellow]⚠ Skipping {label}: {exc}[/yellow]")
            continue

        if not rt.health_check():
            console.print(f"[yellow]⚠ Skipping {label} (not reachable)[/yellow]")
            continue

        results = run_evaluation(rt, test_cases)
        all_results.extend(results)
        summaries.append(summarize(results))
        print_summary(summaries[-1])
        rt.cleanup()

    if len(summaries) > 1:
        print_comparison(summaries)

    if csv_path:
        export_csv(all_results, csv_path)

    if html_path and summaries:
        generate_html_report(summaries, all_results, html_path)
        console.print(f"[green]HTML report exported to {html_path}[/green]")


if __name__ == "__main__":
    main()
