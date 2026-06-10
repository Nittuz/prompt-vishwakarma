"""Record types produced by the eval harness."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScoreResult(BaseModel):
    scorer: str
    value: float  # normalized 0..1
    passed: bool
    detail: str = ""


class ExampleResult(BaseModel):
    id: str
    output: str
    scores: list[ScoreResult] = Field(default_factory=list)
    cost_usd: float = 0.0


class Run(BaseModel):
    run_id: str
    project: str
    prompt: str
    prompt_version: int
    prompt_hash: str
    model: str
    split: str
    examples: list[ExampleResult] = Field(default_factory=list)
    # scorer -> {"mean": x, "pass_rate": y}
    metrics: dict[str, dict[str, float]] = Field(default_factory=dict)
    total_cost_usd: float = 0.0
    created_at: float = 0.0
