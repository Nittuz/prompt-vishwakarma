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


def test_build_scorers_missing_name():
    import pytest

    with pytest.raises(ValueError):
        build_scorers([{"pattern": "x"}])


def test_no_reference_is_explicit():
    e = Example(id="a", input={})  # reference is None
    assert ExactMatch().score(e, "x").detail == "no reference"
    assert Contains().score(e, "x").detail == "no reference"
    assert NumericTolerance().score(e, "5").detail == "no reference"


def test_numeric_handles_sci_and_leading_dot():
    assert NumericTolerance(tol=0).score(Example(id="a", input={}, reference=100000), "= 1e5").passed
    assert NumericTolerance(tol=0).score(Example(id="b", input={}, reference=0.5), "is .5 ok").passed


def test_json_schema_valid_strips_fences_and_flags_no_schema():
    r = JsonSchemaValid().score(Example(id="a", input={}), '```json\n{"k": 1}\n```')
    assert r.passed is True
    assert "no schema" in r.detail
