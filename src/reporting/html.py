"""HTML report generation for evaluation results."""

from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

from src.eval.results import RunSummary
from src.models import EvalResult


def _css() -> str:
    """Inline CSS for the report."""
    return """
    :root { --bg: #0d1117; --surface: #161b22; --border: #30363d;
            --text: #e6edf3; --dim: #8b949e; --green: #3fb950;
            --red: #f85149; --yellow: #d29922; --blue: #58a6ff; }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif;
           background: var(--bg); color: var(--text); padding: 2rem; line-height: 1.5; }
    h1 { margin-bottom: .25rem; }
    .timestamp { color: var(--dim); margin-bottom: 2rem; font-size: .9rem; }
    h2 { color: var(--blue); margin: 2rem 0 1rem; border-bottom: 1px solid var(--border);
         padding-bottom: .4rem; }
    table { border-collapse: collapse; width: 100%; margin-bottom: 1.5rem;
            background: var(--surface); border-radius: 6px; overflow: hidden; }
    th { background: var(--border); text-align: left; padding: .6rem 1rem;
         font-size: .85rem; text-transform: uppercase; letter-spacing: .5px; color: var(--dim); }
    td { padding: .55rem 1rem; border-top: 1px solid var(--border); font-size: .9rem; }
    tr:hover td { background: rgba(88,166,255,.06); }
    .pass { color: var(--green); font-weight: 600; }
    .fail { color: var(--red); font-weight: 600; }
    .skip { color: var(--yellow); }
    .bar-cell { position: relative; }
    .bar { height: 6px; border-radius: 3px; margin-top: 4px; }
    .bar-green { background: var(--green); }
    .bar-red { background: var(--red); }
    .bar-yellow { background: var(--yellow); }
    .section { margin-bottom: 2rem; }
    .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                   gap: 1rem; margin-bottom: 2rem; }
    .metric-card { background: var(--surface); border: 1px solid var(--border);
                   border-radius: 8px; padding: 1rem; text-align: center; }
    .metric-value { font-size: 1.8rem; font-weight: 700; }
    .metric-label { font-size: .8rem; color: var(--dim); margin-top: .2rem; }
    """


def _bar(pct: float) -> str:
    """Render a tiny coloured percentage bar."""
    color = "bar-green" if pct >= 0.9 else ("bar-yellow" if pct >= 0.7 else "bar-red")
    width = max(int(pct * 100), 1)
    return f'<div class="bar {color}" style="width:{width}%"></div>'


def _pct(v: float) -> str:
    cls = "pass" if v >= 0.9 else ("skip" if v >= 0.7 else "fail")
    return f'<span class="{cls}">{v:.1%}</span>'


def _esc(s: str) -> str:
    return html.escape(str(s))


def generate_html_report(
    summaries: list[RunSummary],
    all_results: list[EvalResult],
    path: str | Path,
) -> None:
    """Write a self-contained HTML report to *path*."""
    path = Path(path)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total_tests = summaries[0].total_cases if summaries else 0

    parts: list[str] = []
    parts.append("<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>")
    parts.append("<title>eval-localmodel Report</title>")
    parts.append(f"<style>{_css()}</style></head><body>")
    parts.append("<h1>eval-localmodel Report</h1>")
    parts.append(f'<p class="timestamp">Generated {now} &mdash; {total_tests} test cases</p>')

    # ── Comparison table ──────────────────────────────────────────
    if summaries:
        parts.append("<h2>Comparison</h2>")
        parts.append("<table><thead><tr>")
        parts.append("<th>Runtime / Model</th><th>Full Match</th><th>Tool Select</th>")
        parts.append("<th>Arg Accuracy</th><th>Latency (ms)</th><th>Tokens/sec</th>")
        parts.append("</tr></thead><tbody>")
        for s in summaries:
            parts.append("<tr>")
            parts.append(f"<td><strong>{_esc(s.runtime_name)}/{_esc(s.model_id)}</strong></td>")
            parts.append(f'<td class="bar-cell">{_pct(s.overall_full_match_rate)}{_bar(s.overall_full_match_rate)}</td>')
            parts.append(f'<td class="bar-cell">{_pct(s.overall_tool_selection_rate)}{_bar(s.overall_tool_selection_rate)}</td>')
            parts.append(f'<td class="bar-cell">{_pct(s.overall_arg_accuracy)}{_bar(s.overall_arg_accuracy)}</td>')
            parts.append(f"<td>{s.avg_latency_ms:.0f}</td>")
            parts.append(f"<td>{s.avg_tokens_per_sec:.1f}</td>")
            parts.append("</tr>")
        parts.append("</tbody></table>")

    # ── Per-run category breakdown ────────────────────────────────
    for s in summaries:
        parts.append(f"<h2>{_esc(s.runtime_name)} / {_esc(s.model_id)}</h2>")

        # Metric cards
        parts.append('<div class="metric-grid">')
        for label, value in [
            ("Full Match", f"{s.overall_full_match_rate:.1%}"),
            ("Tool Select", f"{s.overall_tool_selection_rate:.1%}"),
            ("Arg Accuracy", f"{s.overall_arg_accuracy:.1%}"),
            ("Avg Latency", f"{s.avg_latency_ms:.0f} ms"),
            ("Tokens/sec", f"{s.avg_tokens_per_sec:.1f}"),
        ]:
            parts.append(f'<div class="metric-card"><div class="metric-value">{value}</div>')
            parts.append(f'<div class="metric-label">{label}</div></div>')
        parts.append("</div>")

        # Category table
        parts.append("<table><thead><tr>")
        parts.append("<th>Category</th><th>N</th><th>Full Match</th>")
        parts.append("<th>Tool Select</th><th>Arg Acc</th><th>Latency</th><th>Tok/s</th><th>Errors</th>")
        parts.append("</tr></thead><tbody>")
        for cs in s.categories:
            parts.append("<tr>")
            parts.append(f"<td>{_esc(cs.category)}</td><td>{cs.total}</td>")
            parts.append(f"<td>{_pct(cs.full_match_rate)}</td>")
            parts.append(f"<td>{_pct(cs.tool_selection_rate)}</td>")
            parts.append(f"<td>{_pct(cs.avg_arg_accuracy)}</td>")
            parts.append(f"<td>{cs.avg_latency_ms:.0f}</td>")
            parts.append(f"<td>{cs.avg_tokens_per_sec:.1f}</td>")
            parts.append(f"<td>{cs.errors}</td>")
            parts.append("</tr>")
        parts.append("</tbody></table>")

    # ── Per-test detail table ─────────────────────────────────────
    if all_results:
        parts.append("<h2>Per-Test Details</h2>")
        parts.append("<table><thead><tr>")
        parts.append("<th>Test ID</th><th>Category</th><th>Runtime/Model</th>")
        parts.append("<th>Result</th><th>Name</th><th>Arg Acc</th>")
        parts.append("<th>Latency</th><th>Error</th>")
        parts.append("</tr></thead><tbody>")
        for r in all_results:
            if r.error:
                status = '<span class="fail">ERROR</span>'
            elif r.expected_negative:
                status = f'<span class="{"pass" if r.correctly_refused else "fail"}">{"PASS" if r.correctly_refused else "FAIL"}</span>'
            else:
                status = f'<span class="{"pass" if r.full_match else "fail"}">{"PASS" if r.full_match else "FAIL"}</span>'

            name_icon = "✓" if r.tool_name_correct else "✗"
            parts.append("<tr>")
            parts.append(f"<td>{_esc(r.test_id)}</td><td>{_esc(r.category)}</td>")
            parts.append(f"<td>{_esc(r.runtime_name)}/{_esc(r.model_id)}</td>")
            parts.append(f"<td>{status}</td>")
            parts.append(f"<td>{name_icon}</td>")
            parts.append(f"<td>{r.argument_accuracy:.0%}</td>")
            parts.append(f"<td>{r.latency_ms:.0f} ms</td>")
            parts.append(f"<td>{_esc(r.error or '')}</td>")
            parts.append("</tr>")
        parts.append("</tbody></table>")

    parts.append("</body></html>")
    path.write_text("\n".join(parts), encoding="utf-8")
