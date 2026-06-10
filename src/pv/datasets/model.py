"""The Example model — one evaluation/training case."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Example(BaseModel):
    id: str
    input: dict[str, Any] = Field(default_factory=dict)
    reference: Any | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
