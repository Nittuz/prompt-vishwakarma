from pathlib import Path

from pv.generate.base import Brief


def test_brief_defaults():
    b = Brief(idea="x", role="general")
    assert b.analyze == "light"
    assert b.target == "raw"
    assert b.inputs == [] and b.constraints == []
    assert b.repo is None


def test_brief_accepts_repo_and_overrides():
    b = Brief(idea="x", role="code_review", repo=Path("/tmp/r"), analyze="deep", target="claude")
    assert b.repo == Path("/tmp/r")
    assert b.analyze == "deep"
    assert b.target == "claude"
