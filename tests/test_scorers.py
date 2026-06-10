from pv.datasets.model import Example
from pv.eval.scorers import build_scorers
from pv.eval.scorers.deterministic import (
    Contains,
    ExactMatch,
    JsonSchemaValid,
    NumericTolerance,
    Regex,
)


def test_exact_match():
    e = Example(id="a", input={}, reference="yes")
    assert ExactMatch().score(e, " yes ").passed is True
    assert ExactMatch().score(e, "no").passed is False


def test_contains_uses_reference_or_needle():
    e = Example(id="a", input={}, reference="cat")
    assert Contains().score(e, "a cat sat").passed is True
    assert Contains(needle="dog").score(e, "a cat sat").passed is False


def test_regex():
    e = Example(id="a", input={})
    assert Regex(pattern=r"\d{3}").score(e, "id 123").passed is True
    assert Regex(pattern=r"\d{3}").score(e, "id 1").passed is False


def test_json_schema_valid():
    schema = {"type": "object", "properties": {"k": {"type": "integer"}}, "required": ["k"]}
    s = JsonSchemaValid(schema=schema)
    e = Example(id="a", input={})
    assert s.score(e, '{"k": 1}').passed is True
    assert s.score(e, "not json").passed is False
    assert s.score(e, '{"k": "x"}').passed is False


def test_numeric_tolerance():
    e = Example(id="a", input={}, reference=10)
    assert NumericTolerance(tol=1).score(e, "about 10.5").passed is True
    assert NumericTolerance(tol=0.1).score(e, "12").passed is False


def test_build_scorers_mixed_specs():
    scorers = build_scorers(["exact_match", {"name": "regex", "pattern": "x"}])
    assert [s.name for s in scorers] == ["exact_match", "regex"]


def test_build_scorers_judge_requires_runner():
    import pytest

    with pytest.raises(ValueError):
        build_scorers(["llm_judge"], runner=None)
