import pytest

from pv.export import export
from pv.prompts.model import PromptVersion


def _prompt():
    return PromptVersion(
        name="legacy-review",
        description="Review diffs",
        system="You are a reviewer.",
        user="Review {diff}",
    )


def test_export_claude_skill(tmp_path):
    sk = export(_prompt(), "claude", tmp_path)
    assert sk.exists() and sk.name == "SKILL.md"
    text = sk.read_text()
    assert "You are a reviewer." in text
    assert "name: legacy-review" in text
    assert "{diff}" in text


def test_export_cursor_rules(tmp_path):
    cur = export(_prompt(), "cursor", tmp_path)
    assert cur.exists() and cur.suffix == ".mdc"
    assert "You are a reviewer." in cur.read_text()


def test_export_chatgpt_gpt(tmp_path):
    gpt = export(_prompt(), "chatgpt", tmp_path)
    assert gpt.exists()
    text = gpt.read_text()
    assert "Custom GPT" in text and "You are a reviewer." in text


def test_unknown_target(tmp_path):
    with pytest.raises(ValueError):
        export(_prompt(), "telepathy", tmp_path)
