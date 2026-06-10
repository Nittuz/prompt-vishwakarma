"""Export a prompt as a ChatGPT custom-instructions / Custom-GPT spec."""

from __future__ import annotations

from pathlib import Path

from ..prompts.model import PromptVersion
from ..util import slugify
from .base import write


def export_chatgpt_gpt(prompt: PromptVersion, out_dir: Path) -> Path:
    slug = slugify(prompt.name)
    description = prompt.description or f"{prompt.name} assistant."
    starter = prompt.user or "(describe your task)"
    content = (
        f"# ChatGPT Custom GPT — {prompt.name}\n\n"
        "Paste these fields into ChatGPT → Create a GPT (or Custom Instructions).\n\n"
        f"## Name\n{prompt.name}\n\n"
        f"## Description\n{description}\n\n"
        f"## Instructions\n{prompt.system}\n\n"
        f"## Conversation starter (task template)\n{starter}\n"
    )
    return write(out_dir / f"{slug}-gpt.md", content)
