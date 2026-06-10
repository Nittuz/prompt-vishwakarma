from pv.datasets.model import Example
from pv.eval.scorers.llm_judge import LLMJudge
from pv.runners.fake_runner import FakeRunner


def test_judge_normalizes_score():
    def responder(messages, params):
        return {"score": 5, "passed": True, "rationale": "great"}

    j = LLMJudge(FakeRunner(responder))
    r = j.score(Example(id="a", input={"q": "x"}, reference="y"), "an answer")
    assert r.value == 1.0  # (5-1)/4
    assert r.passed is True
    assert r.detail == "great"


def test_judge_low_score():
    def responder(messages, params):
        return {"score": 1, "passed": False, "rationale": "bad"}

    r = LLMJudge(FakeRunner(responder)).score(Example(id="a", input={}), "x")
    assert r.value == 0.0
    assert r.passed is False
