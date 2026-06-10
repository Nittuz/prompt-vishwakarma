"""Export a prompt as a Claude Code skill folder (`<slug>/SKILL.md`)."""

from __future__ import annotations

from pathlib import Path

from ..prompts.model import PromptVersion
from ..util import slugify
from .base import body, write


def export_claude_skill(prompt: PromptVersion, out_dir: Path) -> Path:
    slug = slugify(prompt.name)
    description = prompt.description or f"{prompt.name} prompt."
    content = (
        "---\n"
        f"name: {slug}\n"
        f"description: {description}\n"
        "---\n\n"
        f"# {prompt.name}\n\n"
        f"{body(prompt)}\n"
    )
    return write(out_dir / slug / "SKILL.md", content)
