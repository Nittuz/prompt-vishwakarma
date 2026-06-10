from pv.generate.critique import critique
from pv.prompts.model import PromptVersion
from pv.runners.fake_runner import FakeRunner


def test_critique_revises():
    p = PromptVersion(name="x", role="general", system="old", user="old {v}")

    def responder(messages, params):
        return {"system": "new", "user": "new {v}", "changes": "tightened"}

    revised, changes = critique(FakeRunner(responder), p)
    assert revised.system == "new"
    assert revised.user == "new {v}"
    assert changes == "tightened"
    assert revised.name == "x"  # identity preserved


def test_critique_without_role_uses_general_practices():
    p = PromptVersion(name="x", role=None, system="s", user="u")
    captured = {}

    def responder(messages, params):
        captured["msg"] = messages[-1].content
        return {"system": "s2", "user": "u2", "changes": "c"}

    critique(FakeRunner(responder), p)
    assert "general best practices" in captured["msg"]
