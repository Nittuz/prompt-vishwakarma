"""Export a prompt into a portable artifact usable today."""

from __future__ import annotations

from pathlib import Path

from ..prompts.model import PromptVersion
from .chatgpt_gpt import export_chatgpt_gpt
from .claude_skill import export_claude_skill
from .cursor_rules import export_cursor_rules

_TARGETS = {
    "claude": export_claude_skill,
    "cursor": export_cursor_rules,
    "chatgpt": export_chatgpt_gpt,
}


def export(prompt: PromptVersion, target: str, out_dir: Path) -> Path:
    if target not in _TARGETS:
        raise ValueError(f"unknown export target: {target!r} (have {sorted(_TARGETS)})")
    return _TARGETS[target](prompt, Path(out_dir))


__all__ = ["export", "export_claude_skill", "export_cursor_rules", "export_chatgpt_gpt"]
