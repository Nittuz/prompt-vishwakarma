from pv.generate.base import Brief
from pv.generate.meta_prompt import build_meta_prompt, generate
from pv.roles.model import load_role
from pv.runners.fake_runner import FakeRunner
from pv.util import slugify


def test_meta_prompt_includes_role_and_repo():
    b = Brief(idea="design a feature", role="feature_design", inputs=["feature"])
    meta = build_meta_prompt(
        b,
        load_role("feature_design"),
        {"stack": "next.js", "conventions": ["app router"], "reusable": ["Button"], "risks": []},
    )
    assert "feature_design" in meta
    assert "next.js" in meta
    assert "placeholders" in meta
    assert "feature" in meta


def test_meta_prompt_no_repo_summary_but_repo_present():
    b = Brief(idea="review", role="code_review", repo="/tmp/r")
    meta = build_meta_prompt(b, load_role("code_review"), None)
    assert "inspect the repository" in meta.lower()


def test_generate_returns_promptversion():
    def responder(messages, params):
        return {
            "description": "d",
            "system": "You are X.",
            "user": "Do {feature}",
            "rationale": "r",
        }

    pv, rationale = generate(FakeRunner(responder), Brief(idea="My MBR agenda!", role="meeting"))
    assert pv.system == "You are X."
    assert "{feature}" in pv.user
    assert pv.name == slugify("My MBR agenda!")
    assert pv.role == "meeting"
    assert rationale == "r"
