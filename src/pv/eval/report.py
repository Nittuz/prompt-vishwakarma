"""Render eval runs as Markdown, and compare two runs."""

from __future__ import annotations

from .result import Run


def render_report(run: Run) -> str:
    lines = [
        f"# Eval: {run.project} / {run.prompt} v{run.prompt_version}",
        f"- model: {run.model}  ·  split: {run.split}  ·  examples: {len(run.examples)}",
        f"- run_id: {run.run_id}  ·  cost: ${run.total_cost_usd:.4f}",
        "",
        "## Metrics",
        "",
        "| scorer | mean | pass rate |",
        "| --- | --- | --- |",
    ]
    for name, m in run.metrics.items():
        lines.append(f"| {name} | {m.get('mean', 0.0):.3f} | {m.get('pass_rate', 0.0):.0%} |")
    lines += ["", "## Examples", "", "| id | scores | output (truncated) |", "| --- | --- | --- |"]
    for r in run.examples:
        sc = " ".join(f"{s.scorer}={s.value:.2f}" for s in r.scores)
        out = r.output.replace("\n", " ").replace("|", "\\|")[:80]
        lines.append(f"| {r.id} | {sc} | {out} |")
    return "\n".join(lines) + "\n"


def compare(a: Run, b: Run) -> str:
    scorers = sorted(set(a.metrics) | set(b.metrics))
    lines = [
        f"# Compare: {a.run_id} vs {b.run_id}",
        "",
        "| scorer | A mean | B mean | Δ |",
        "| --- | --- | --- | --- |",
    ]
    for s in scorers:
        am = a.metrics.get(s, {}).get("mean", 0.0)
        bm = b.metrics.get(s, {}).get("mean", 0.0)
        lines.append(f"| {s} | {am:.3f} | {bm:.3f} | {bm - am:+.3f} |")
    lines += ["", f"- cost: A ${a.total_cost_usd:.4f}  ·  B ${b.total_cost_usd:.4f}"]
    return "\n".join(lines) + "\n"
