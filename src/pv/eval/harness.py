"""The eval harness: render a prompt per example, call the engine, score, record."""

from __future__ import annotations

import time
from statistics import mean

from ..datasets.model import Example
from ..prompts.model import PromptVersion
from ..runners.base import GenParams, Message
from .result import ExampleResult, Run, ScoreResult


def _run_id(project: str, split: str) -> str:
    return f"{project or 'lib'}-{split}-{int(time.time())}"


def _check_inputs(prompt: PromptVersion, examples: list[Example]) -> None:
    needed = prompt.variables()
    missing = {e.id: sorted(needed - set(e.input)) for e in examples if needed - set(e.input)}
    if missing:
        raise ValueError(f"examples missing prompt variables: {missing}")


def run_eval(
    runner,
    prompt: PromptVersion,
    examples: list[Example],
    scorers: list,
    model: str = "opus",
    project: str = "",
    split: str = "dev",
) -> Run:
    _check_inputs(prompt, examples)
    results: list[ExampleResult] = []
    for e in examples:
        before = getattr(runner, "total_cost", 0.0)
        system, user = prompt.render(e.input)
        resp = runner.complete(
            [Message(role="user", content=user)],
            GenParams(model=model, system=system or None),
        )
        scores = [s.score(e, resp.text) for s in scorers]
        cost = getattr(runner, "total_cost", 0.0) - before
        results.append(ExampleResult(id=e.id, output=resp.text, scores=scores, cost_usd=cost))

    return Run(
        run_id=_run_id(project, split),
        project=project,
        prompt=prompt.name,
        prompt_version=prompt.version,
        prompt_hash=prompt.content_hash,
        model=getattr(runner, "last_model", "") or model,
        split=split,
        examples=results,
        metrics=_aggregate(results),
        total_cost_usd=round(sum(r.cost_usd for r in results), 6),
        created_at=time.time(),
    )


def _aggregate(results: list[ExampleResult]) -> dict:
    by: dict[str, list[ScoreResult]] = {}
    for r in results:
        for s in r.scores:
            by.setdefault(s.scorer, []).append(s)
    return {
        name: {
            "mean": round(mean(s.value for s in lst), 4),
            "pass_rate": round(mean(1.0 if s.passed else 0.0 for s in lst), 4),
        }
        for name, lst in by.items()
    }
