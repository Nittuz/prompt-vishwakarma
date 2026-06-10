"""Shared helpers for exporters."""

from __future__ import annotations

from pathlib import Path

from ..prompts.model import PromptVersion


def body(prompt: PromptVersion) -> str:
    """The reusable instruction body shared across export targets."""
    sections = []
    if prompt.system:
        sections.append(f"## Instructions\n\n{prompt.system}")
    if prompt.user:
        sections.append(f"## Task template\n\n{prompt.user}")
    if prompt.variables():
        vars_list = ", ".join(f"`{{{v}}}`" for v in sorted(prompt.variables()))
        sections.append(f"## Variables\n\nFill in at use-time: {vars_list}")
    return "\n\n".join(sections)


def write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path
