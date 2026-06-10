from pv.datasets.io import append_jsonl, load_jsonl, stats, validate, write_jsonl
from pv.datasets.model import Example


def _ex(i, **inp):
    return Example(id=i, input=inp, reference=inp.get("ref"))


def test_write_load_roundtrip(tmp_path):
    p = tmp_path / "dev.jsonl"
    exs = [Example(id="a", input={"x": "1"}, reference="r"), Example(id="b", input={"x": "2"})]
    write_jsonl(p, exs)
    loaded = load_jsonl(p)
    assert [e.id for e in loaded] == ["a", "b"]
    assert loaded[0].reference == "r"


def test_load_missing_is_empty(tmp_path):
    assert load_jsonl(tmp_path / "nope.jsonl") == []


def test_validate_flags_dups_and_missing():
    exs = [Example(id="a", input={"x": 1}), Example(id="a", input={})]
    problems = validate(exs, required_inputs=["x"])
    assert any("duplicate" in p for p in problems)
    assert any("missing input field 'x'" in p for p in problems)


def test_stats_counts():
    exs = [Example(id="a", input={"x": 1}, reference="r"), Example(id="b", input={"x": 2, "y": 3})]
    s = stats(exs)
    assert s["count"] == 2
    assert s["with_reference"] == 1
    assert s["input_fields"]["x"] == 2 and s["input_fields"]["y"] == 1


def test_append(tmp_path):
    p = tmp_path / "dev.jsonl"
    write_jsonl(p, [Example(id="a", input={})])
    append_jsonl(p, [Example(id="b", input={})])
    assert [e.id for e in load_jsonl(p)] == ["a", "b"]
