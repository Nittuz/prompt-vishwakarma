"""Repo-aware grounding: scan a repository and summarize it for the generator.

Toggle: ``off`` (skip), ``light`` (quick scan, default), ``deep`` (thorough).
Runs the runner with read tools enabled so Claude can inspect files.
"""

from __future__ import annotations

from pathlib import Path

from ..runners.base import GenParams, Message, Runner

REPO_SCHEMA = {
    "type": "object",
    "properties": {
        "stack": {"type": "string"},
        "conventions": {"type": "array", "items": {"type": "string"}},
        "reusable": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["stack", "conventions", "reusable", "risks"],
    "additionalProperties": False,
}


def analyze(runner: Runner, repo: Path, depth: str = "light") -> dict | None:
    """Return a structured repo summary, or ``None`` when depth is ``off``."""
    if depth == "off":
        return None
    scope = (
        "Skim only the manifest(s) and the top-level directory structure."
        if depth == "light"
        else "Inspect key directories, component/util/test patterns, and risks in depth."
    )
    message = (
        f"Analyze the repository at {repo}. {scope} "
        "Report: the tech stack, the dominant conventions (routing, state, "
        "styling, file layout), reusable modules worth building on, and notable "
        "risks. Be concise."
    )
    resp = runner.complete(
        [Message(role="user", content=message)],
        GenParams(
            model="opus",
            tools=["Read", "Glob", "Grep"],
            json_schema=REPO_SCHEMA,
            max_tokens=2048,
        ),
    )
    return resp.structured or None
