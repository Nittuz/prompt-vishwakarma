import pytest

from pv.prompts.model import PromptVersion
from pv.prompts.registry import PromptStore


def test_render_and_missing():
    p = PromptVersion(name="x", system="Role.", user="Hi {who}")
    assert p.render({"who": "Sam"}) == ("Role.", "Hi Sam")
    with pytest.raises(KeyError):
        p.render({})


def test_render_leaves_json_braces_untouched():
    p = PromptVersion(name="x", system="", user='Return {"k": 1} for {who}')
    sys, user = p.render({"who": "Sam"})
    assert user == 'Return {"k": 1} for Sam'


def test_content_hash_changes_with_content():
    a = PromptVersion(name="x", system="s", user="u")
    b = PromptVersion(name="x", system="s", user="u2")
    assert a.content_hash != b.content_hash


def test_invalid_name_rejected(tmp_path):
    s = PromptStore(tmp_path)
    for bad in ["../evil", "a/b", "..", "x\\y"]:
        with pytest.raises(ValueError):
            s.versions(bad)


def test_versioning(tmp_path):
    s = PromptStore(tmp_path)
    a = s.save_new_version(PromptVersion(name="agenda", system="s", user="u {x}"))
    assert a.version == 1
    b = s.save_new_version(PromptVersion(name="agenda", system="s2", user="u2 {x}"))
    assert b.version == 2
    assert s.versions("agenda") == [1, 2]
    assert s.load("agenda").version == 2
    assert s.load("agenda", 1).system == "s"
    assert s.list() == ["agenda"]
