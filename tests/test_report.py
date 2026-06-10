from pv.eval.report import compare, render_report
from pv.eval.result import ExampleResult, Run, ScoreResult


def _run(run_id, mean_val):
    return Run(
        run_id=run_id,
        project="demo",
        prompt="p",
        prompt_version=1,
        prompt_hash="h",
        model="opus",
        split="dev",
        examples=[
            ExampleResult(
                id="a",
                output="hello",
                scores=[ScoreResult(scorer="exact_match", value=mean_val, passed=mean_val >= 0.5)],
            )
        ],
        metrics={"exact_match": {"mean": mean_val, "pass_rate": mean_val}},
        total_cost_usd=0.01,
    )


def test_render_report_has_metrics_and_examples():
    md = render_report(_run("r1", 1.0))
    assert "## Metrics" in md
    assert "exact_match" in md
    assert "| a |" in md


def test_compare_shows_delta():
    md = compare(_run("r1", 0.5), _run("r2", 0.8))
    assert "Δ" in md
    assert "+0.300" in md
