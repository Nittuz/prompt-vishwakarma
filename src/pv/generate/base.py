"""The generation input: a Brief."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class Brief(BaseModel):
    idea: str
    role: str
    workflow_notes: str | None = None
    audience: str | None = None
    inputs: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    output_shape: str | None = None
    target: Literal["claude", "cursor", "chatgpt", "raw"] = "raw"
    repo: Path | None = None
    analyze: Literal["off", "light", "deep"] = "light"
