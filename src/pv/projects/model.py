"""The Project model (mirrors project.yaml)."""

from __future__ import annotations

from pydantic import BaseModel, Field


def _default_models() -> dict[str, str]:
    return {"primary": "opus", "judge": "opus"}


def _default_datasets() -> dict[str, str]:
    return {
        "train": "datasets/train.jsonl",
        "dev": "datasets/dev.jsonl",
        "test": "datasets/test.jsonl",
    }


class Project(BaseModel):
    name: str
    role: str = "general"
    runner: str = "claude"
    models: dict[str, str] = Field(default_factory=_default_models)
    datasets: dict[str, str] = Field(default_factory=_default_datasets)
    scorers: list = Field(default_factory=lambda: ["llm_judge"])
    optimize: dict = Field(default_factory=dict)
    distill: dict = Field(default_factory=dict)
