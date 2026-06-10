from pathlib import Path

from pv.generate.repo_analysis import analyze
from pv.runners.fake_runner import FakeRunner


def test_off_returns_none():
    assert analyze(FakeRunner(), Path("."), "off") is None


def test_light_calls_runner_with_read_tools():
    captured = {}

    def responder(messages, params):
        captured["tools"] = params.tools
        captured["schema"] = params.json_schema is not None
        captured["add_dir"] = params.add_dir
        return {
            "stack": "next.js",
            "conventions": ["app router"],
            "reusable": ["Button"],
            "risks": [],
        }

    out = analyze(FakeRunner(responder), Path("/x"), "light")
    assert out["stack"] == "next.js"
    assert "Read" in captured["tools"]
    assert captured["schema"] is True
    assert captured["add_dir"] == "/x"  # repo granted to the engine's file tools


def test_deep_uses_thorough_scope():
    captured = {}

    def responder(messages, params):
        captured["msg"] = messages[-1].content
        return {"stack": "", "conventions": [], "reusable": [], "risks": []}

    analyze(FakeRunner(responder), Path("/x"), "deep")
    assert "in depth" in captured["msg"]
