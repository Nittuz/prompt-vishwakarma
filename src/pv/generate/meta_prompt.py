"""The meta-prompt: a prompt that writes prompts, parameterized by the role."""

from __future__ import annotations

from ..prompts.model import PromptVersion
from ..roles.model import Role, load_role
from ..runners.base import GenParams, Message, Runner
from ..util import slugify
from .base import Brief

GEN_SCHEMA = {
    "type": "object",
    "properties": {
        "description": {"type": "string"},
        "system": {"type": "string"},
        "user": {"type": "string"},
        "rationale": {"type": "string"},
    },
    "required": ["description", "system", "user", "rationale"],
    "additionalProperties": False,
}


def _fmt_repo(summary: dict) -> str:
    return (
        f"Stack: {summary.get('stack', '')}\n"
        f"Conventions: {', '.join(summary.get('conventions', []))}\n"
        f"Reusable: {', '.join(summary.get('reusable', []))}\n"
        f"Risks: {', '.join(summary.get('risks', []))}"
    )


def build_meta_prompt(brief: Brief, role: Role, repo_summary: dict | None) -> str:
    parts = [
        "You are an expert prompt engineer. Write a high-quality, REUSABLE prompt "
        "that another AI will run later to accomplish the task below. Return JSON "
        "matching the provided schema — do not include anything else.",
        f"# Task idea\n{brief.idea}",
        f"# Role: {role.name}\n{role.description}",
        "# Required sections (the prompt should cover these)\n"
        + "\n".join(f"- {s}" for s in role.sections),
        "# Best-practice checklist (follow these when writing the prompt)\n"
        + "\n".join(f"- {c}" for c in role.checklist),
    ]
    if brief.workflow_notes:
        parts.append(f"# Workflow / how it should operate\n{brief.workflow_notes}")
    if brief.audience:
        parts.append(f"# Audience\n{brief.audience}")
    if brief.inputs:
        parts.append(
            "# Inputs available at use-time (reference them as {placeholders})\n"
            + "\n".join(f"- {i}" for i in brief.inputs)
        )
    if brief.constraints:
        parts.append("# Constraints\n" + "\n".join(f"- {c}" for c in brief.constraints))
    if brief.output_shape:
        parts.append(f"# Desired output shape\n{brief.output_shape}")
    if repo_summary:
        parts.append(
            "# Repository analysis (bake these specifics into the prompt)\n"
            + _fmt_repo(repo_summary)
        )
    else:
        if brief.repo is not None:
            parts.append(
                "# Repository\nThe prompt will be used inside a repo. Instruct the "
                "downstream agent to inspect the repository before acting."
            )
    parts.append(f"# Target surface for the final prompt\n{brief.target}")
    parts.append(
        "Output guidance: the 'system' field is the persona + rules; the 'user' "
        "field is the task template with {curly_brace} variables the user fills at "
        "run-time. 'description' is one line. 'rationale' explains your choices."
    )
    return "\n\n".join(parts)


def generate(
    runner: Runner, brief: Brief, repo_summary: dict | None = None
) -> tuple[PromptVersion, str]:
    role = load_role(brief.role)
    meta = build_meta_prompt(brief, role, repo_summary)
    resp = runner.complete(
        [Message(role="user", content=meta)],
        GenParams(json_schema=GEN_SCHEMA),
    )
    data = resp.structured
    if not data or not data.get("system") or not data.get("user"):
        raise RuntimeError(
            "the engine did not return a structured prompt (system/user missing). "
            "Try again, or use --no-cache."
        )
    prompt = PromptVersion(
        name=slugify(brief.idea),
        role=brief.role,
        description=data.get("description", ""),
        defaults={"model": "opus"},
        system=data.get("system", ""),
        user=data.get("user", ""),
    )
    return prompt, data.get("rationale", "")
