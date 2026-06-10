"""Scorer registry + builder.

A scorer spec is either a bare name (``"exact_match"``) or a dict with a
``name`` plus config (``{"name": "regex", "pattern": "..."}``).
"""

from __future__ import annotations

from .base import Scorer
from .deterministic import (
    Contains,
    ExactMatch,
    JsonSchemaValid,
    NumericTolerance,
    Regex,
)
from .llm_judge import DEFAULT_RUBRIC, LLMJudge

_DETERMINISTIC = {
    c.name: c for c in [ExactMatch, Contains, Regex, JsonSchemaValid, NumericTolerance]
}


def build_scorers(specs: list, runner=None, judge_model: str = "opus") -> list[Scorer]:
    scorers: list[Scorer] = []
    for spec in specs:
        if isinstance(spec, str):
            name, cfg = spec, {}
        else:
            cfg = dict(spec)
            name = cfg.pop("name", None)
            if name is None:
                raise ValueError(f"scorer spec missing 'name': {spec!r}")
        if name == "llm_judge":
            if runner is None:
                raise ValueError("llm_judge requires a runner")
            scorers.append(
                LLMJudge(
                    runner,
                    model=cfg.get("model", judge_model),
                    rubric=cfg.get("rubric", DEFAULT_RUBRIC),
                )
            )
        elif name in _DETERMINISTIC:
            scorers.append(_DETERMINISTIC[name](**cfg))
        else:
            raise ValueError(f"unknown scorer: {name!r}")
    return scorers


__all__ = ["build_scorers"]
