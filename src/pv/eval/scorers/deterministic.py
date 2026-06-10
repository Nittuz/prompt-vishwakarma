"""Deterministic scorers (no model calls)."""

from __future__ import annotations

import json
import re

from jsonschema import Draft202012Validator

from ...datasets.model import Example
from ..result import ScoreResult


class ExactMatch:
    name = "exact_match"

    def score(self, e: Example, output: str) -> ScoreResult:
        ok = output.strip() == str(e.reference).strip()
        return ScoreResult(
            scorer=self.name,
            value=1.0 if ok else 0.0,
            passed=ok,
            detail="" if ok else f"expected {e.reference!r}",
        )


class Contains:
    name = "contains"

    def __init__(self, needle: str | None = None):
        self.needle = needle

    def score(self, e: Example, output: str) -> ScoreResult:
        needle = self.needle if self.needle is not None else str(e.reference)
        ok = needle in output
        return ScoreResult(scorer=self.name, value=1.0 if ok else 0.0, passed=ok)


class Regex:
    name = "regex"

    def __init__(self, pattern: str):
        self.rx = re.compile(pattern)

    def score(self, e: Example, output: str) -> ScoreResult:
        ok = bool(self.rx.search(output))
        return ScoreResult(scorer=self.name, value=1.0 if ok else 0.0, passed=ok)


class JsonSchemaValid:
    name = "json_schema_valid"

    def __init__(self, schema: dict | None = None):
        self.schema = schema

    def score(self, e: Example, output: str) -> ScoreResult:
        schema = self.schema or e.metadata.get("schema")
        try:
            data = json.loads(output)
        except json.JSONDecodeError as ex:
            return ScoreResult(scorer=self.name, value=0.0, passed=False, detail=f"not JSON: {ex}")
        if schema:
            errors = sorted(Draft202012Validator(schema).iter_errors(data), key=str)
            if errors:
                return ScoreResult(
                    scorer=self.name, value=0.0, passed=False, detail=errors[0].message
                )
        return ScoreResult(scorer=self.name, value=1.0, passed=True)


class NumericTolerance:
    name = "numeric_tolerance"

    def __init__(self, tol: float = 0.0):
        self.tol = tol

    def score(self, e: Example, output: str) -> ScoreResult:
        m = re.search(r"-?\d+(\.\d+)?", output)
        if not m:
            return ScoreResult(scorer=self.name, value=0.0, passed=False, detail="no number found")
        try:
            ok = abs(float(m.group()) - float(e.reference)) <= self.tol
        except (TypeError, ValueError):
            return ScoreResult(scorer=self.name, value=0.0, passed=False, detail="bad reference")
        return ScoreResult(scorer=self.name, value=1.0 if ok else 0.0, passed=ok)
