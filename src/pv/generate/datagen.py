"""Synthesize seed dataset examples for a prompt via Claude (curate after)."""

from __future__ import annotations

import json

from ..datasets.model import Example
from ..prompts.model import PromptVersion
from ..runners.base import GenParams, Message

GEN_SCHEMA = {
    "type": "object",
    "properties": {
        "examples": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    # input carried as a JSON string to allow arbitrary keys
                    "input_json": {"type": "string"},
                    "reference": {"type": "string"},
                },
                "required": ["input_json"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["examples"],
    "additionalProperties": False,
}


def gen_examples(runner, prompt: PromptVersion, n: int = 5, model: str = "opus") -> list[Example]:
    variables = sorted(prompt.variables())
    msg = (
        f"Generate {n} diverse, realistic test examples for the prompt below. "
        f"Each example's input_json MUST be a JSON object with exactly these keys: "
        f"{variables}. Where it makes sense, also give a concise 'reference' "
        "(the ideal/expected answer).\n\n"
        f"PROMPT SYSTEM:\n{prompt.system}\n\nPROMPT USER TEMPLATE:\n{prompt.user}"
    )
    resp = runner.complete(
        [Message(role="user", content=msg)],
        GenParams(model=model, json_schema=GEN_SCHEMA),
    )
    data = resp.structured or {}
    out: list[Example] = []
    for i, item in enumerate(data.get("examples", []), 1):
        try:
            inp = json.loads(item["input_json"])
        except Exception:
            continue
        if not isinstance(inp, dict):
            continue
        out.append(Example(id=f"gen-{i}", input=inp, reference=item.get("reference")))
    return out
