import json

from pv.runners.base import GenParams, Message
from pv.runners.claude_runner import ClaudeRunner
from pv.runners.fake_runner import FakeRunner, fill_schema
from pv.runners.registry import get_runner


def test_build_command_pure_mode():
    cmd = ClaudeRunner().build_command(GenParams(model="opus"))
    assert cmd[:2] == ["claude", "-p"]
    assert "--output-format" in cmd and "json" in cmd
    assert "--model" in cmd and "claude-opus-4-8" in cmd
    i = cmd.index("--tools")
    assert cmd[i + 1] == ""  # pure mode


def test_build_command_tools_and_schema():
    p = GenParams(
        model="sonnet",
        tools=["Read", "Glob"],
        json_schema={"type": "object"},
        system="be terse",
    )
    cmd = ClaudeRunner().build_command(p)
    assert "--allowedTools" in cmd and "Read,Glob" in cmd
    assert "--json-schema" in cmd
    assert "--append-system-prompt" in cmd and "be terse" in cmd
    assert "--tools" not in cmd  # tools requested → not pure mode


def test_parse_json_output():
    out = json.dumps(
        {
            "result": "hello",
            "total_cost_usd": 0.02,
            "usage": {"input_tokens": 5, "output_tokens": 3},
            "structured_output": {"k": "v"},
            "modelUsage": {"claude-opus-4-8": {}},
        }
    )
    r = ClaudeRunner.parse(out)
    assert r.text == "hello"
    assert r.usage.cost_usd == 0.02
    assert r.usage.input_tokens == 5
    assert r.structured == {"k": "v"}
    assert r.model == "claude-opus-4-8"


def test_render_stdin_drops_system():
    msgs = [
        Message(role="system", content="SYS"),
        Message(role="user", content="hello"),
    ]
    assert ClaudeRunner.render_stdin(msgs) == "hello"


def test_registry_fake(monkeypatch):
    monkeypatch.setenv("PV_RUNNER", "fake")
    r = get_runner("claude")
    assert r.name == "fake"
    resp = r.complete([Message(role="user", content="hi")], GenParams())
    assert resp.text.startswith("FAKE")


def test_fake_runner_fills_schema():
    schema = {
        "type": "object",
        "properties": {"system": {"type": "string"}, "items": {"type": "array"}},
        "required": ["system", "items"],
    }
    out = fill_schema(schema)
    assert out["system"] == "fake system"
    assert out["items"] == []

    resp = FakeRunner().complete([], GenParams(json_schema=schema))
    assert resp.structured == out
