"""Export a prompt as a Cursor project rule (`<slug>.mdc`)."""

from __future__ import annotations

from pathlib import Path

from ..prompts.model import PromptVersion
from ..util import slugify
from .base import body, write


def export_cursor_rules(prompt: PromptVersion, out_dir: Path) -> Path:
    slug = slugify(prompt.name)
    description = prompt.description or f"{prompt.name} rule."
    content = (
        "---\n"
        f"description: {description}\n"
        "alwaysApply: false\n"
        "---\n\n"
        f"# {prompt.name}\n\n"
        f"{body(prompt)}\n"
    )
    return write(out_dir / f"{slug}.mdc", content)
