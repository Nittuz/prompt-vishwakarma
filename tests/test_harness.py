import pytest

from pv.datasets.model import Example
from pv.eval.harness import run_eval
from pv.eval.scorers.deterministic import ExactMatch
from pv.eval.scorers.llm_judge import LLMJudge
from pv.prompts.model import PromptVersion
from pv.runners.fake_runner import FakeRunner


def test_run_eval_aggregates_metrics():
    prompt = PromptVersion(name="p", system="be terse", user="Answer: {q}")
    examples = [
        Example(id="a", input={"q": "1"}, reference="FAKE: Answer: 1"),
        Example(id="b", input={"q": "2"}, reference="nope"),
    ]
    # FakeRunner (no responder) echoes "FAKE: " + last user message → "FAKE: Answer: 1"
    run = run_eval(FakeRunner(), prompt, examples, [ExactMatch()], model="haiku", project="demo")
    assert run.metrics["exact_match"]["pass_rate"] == 0.5  # a matches, b doesn't
    assert len(run.examples) == 2
    assert run.split == "dev"


def test_run_eval_missing_variable_raises():
    prompt = PromptVersion(name="p", user="Answer: {q}")
    with pytest.raises(ValueError):
        run_eval(FakeRunner(), prompt, [Example(id="a", input={})], [ExactMatch()])


def test_run_eval_with_judge():
    prompt = PromptVersion(name="p", user="Q: {q}")

    def responder(messages, params):
        # judge calls carry a json_schema; generation does not
        if params.json_schema is not None:
            return {"score": 5, "passed": True, "rationale": "ok"}
        return "an answer"

    runner = FakeRunner(responder)
    run = run_eval(runner, prompt, [Example(id="a", input={"q": "x"})], [LLMJudge(runner)])
    assert run.metrics["llm_judge"]["mean"] == 1.0
