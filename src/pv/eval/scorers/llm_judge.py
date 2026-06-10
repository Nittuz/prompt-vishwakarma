"""Claude-as-judge scorer (structured output). Default model: opus."""

from __future__ import annotations

from ...datasets.model import Example
from ...runners.base import GenParams, Message
from ..result import ScoreResult

JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "passed": {"type": "boolean"},
        "rationale": {"type": "string"},
    },
    "required": ["score", "passed", "rationale"],
    "additionalProperties": False,
}

DEFAULT_RUBRIC = (
    "Judge how well the OUTPUT accomplishes the task for the given INPUT "
    "(and REFERENCE if present). Score 1-5 (5 = excellent). passed = score >= 4."
)


class LLMJudge:
    name = "llm_judge"

    def __init__(self, runner, model: str = "opus", rubric: str = DEFAULT_RUBRIC):
        self.runner = runner
        self.model = model
        self.rubric = rubric

    def score(self, e: Example, output: str) -> ScoreResult:
        ref = "" if e.reference is None else f"\nREFERENCE:\n{e.reference}"
        msg = (
            f"{self.rubric}\n\nINPUT:\n{e.input}{ref}\n\nOUTPUT:\n{output}\n\n"
            "Return JSON with: score (1-5 integer), passed (boolean), rationale (string)."
        )
        resp = self.runner.complete(
            [Message(role="user", content=msg)],
            GenParams(model=self.model, json_schema=JUDGE_SCHEMA),
        )
        d = resp.structured or {}
        score = int(d.get("score", 0))
        value = max(0.0, min(1.0, (score - 1) / 4)) if score else 0.0
        return ScoreResult(
            scorer=self.name,
            value=value,
            passed=bool(d.get("passed", score >= 4)),
            detail=d.get("rationale", ""),
        )
