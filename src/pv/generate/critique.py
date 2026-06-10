"""Single-shot critique → revised prompt version (no dataset needed)."""

from __future__ import annotations

from ..prompts.model import PromptVersion
from ..roles.model import load_role
from ..runners.base import GenParams, Message, Runner

CRIT_SCHEMA = {
    "type": "object",
    "properties": {
        "system": {"type": "string"},
        "user": {"type": "string"},
        "changes": {"type": "string"},
    },
    "required": ["system", "user", "changes"],
    "additionalProperties": False,
}


def critique(runner: Runner, prompt: PromptVersion) -> tuple[PromptVersion, str]:
    role = load_role(prompt.role) if prompt.role else None
    checklist = "\n".join(f"- {c}" for c in (role.checklist if role else []))
    message = (
        "Critique and improve the prompt below against the checklist, then return "
        "the revised system/user and a short summary of the changes you made.\n\n"
        f"# Checklist\n{checklist or '- (no role checklist; apply general best practices)'}\n\n"
        f"# Current system\n{prompt.system}\n\n"
        f"# Current user\n{prompt.user}"
    )
    resp = runner.complete(
        [Message(role="user", content=message)],
        GenParams(json_schema=CRIT_SCHEMA),
    )
    data = resp.structured
    if not data or not data.get("system") or not data.get("user"):
        raise RuntimeError(
            "the engine did not return a structured revision (system/user missing). "
            "Try again, or use --no-cache."
        )
    revised = prompt.model_copy(
        update={
            "system": data.get("system", prompt.system),
            "user": data.get("user", prompt.user),
        }
    )
    return revised, data.get("changes", "")
