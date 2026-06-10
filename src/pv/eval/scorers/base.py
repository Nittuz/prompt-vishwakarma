"""Scorer protocol."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ...datasets.model import Example
from ..result import ScoreResult


@runtime_checkable
class Scorer(Protocol):
    name: str

    def score(self, example: Example, output: str) -> ScoreResult:
        ...
