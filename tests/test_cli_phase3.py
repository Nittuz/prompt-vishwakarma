import json

from typer.testing import CliRunner

from pv.cli import app

runner = CliRunner()


def _mark_root(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")


def _setup_project_with_prompt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PV_RUNNER", "fake")
    _mark_root(tmp_path)
    # generate a library prompt, then promote into a project
    runner.invoke(app, ["new", "answer questions", "--role", "extract", "--no-analyze"])
    name = next((tmp_path / "library").iterdir()).name
    r = runner.invoke(app, ["promote", name, "--to-project", "demo"])
    assert r.exit_code == 0, r.output
    return name


def test_init_creates_project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PV_RUNNER", "fake")
    _mark_root(tmp_path)
    r = runner.invoke(app, ["init", "demo", "--role", "extract"])
    assert r.exit_code == 0, r.output
    assert (tmp_path / "projects" / "demo" / "project.yaml").exists()


def test_promote_then_eval(tmp_path, monkeypatch):
    name = _setup_project_with_prompt(tmp_path, monkeypatch)
    # the promoted extract prompt uses {input}; write a dev split
    dev = tmp_path / "projects" / "demo" / "datasets" / "dev.jsonl"
    dev.write_text(
        "\n".join(
            json.dumps({"id": f"e{i}", "input": {"input": f"case {i}"}, "reference": "x"})
            for i in range(2)
        )
    )
    r = runner.invoke(app, ["eval", "--project", "demo", "--split", "dev"])
    assert r.exit_code == 0, r.output
    runs = list((tmp_path / "projects" / "demo" / "runs").glob("*/run.json"))
    assert runs, r.output
    reports = list((tmp_path / "projects" / "demo" / "runs").glob("*/report.md"))
    assert reports


def test_data_stats(tmp_path, monkeypatch):
    _setup_project_with_prompt(tmp_path, monkeypatch)
    dev = tmp_path / "projects" / "demo" / "datasets" / "dev.jsonl"
    dev.write_text(json.dumps({"id": "e1", "input": {"input": "x"}}))
    r = runner.invoke(app, ["data", "stats", "--project", "demo", "--split", "dev"])
    assert r.exit_code == 0, r.output
    assert "1 examples" in r.output


def test_eval_without_examples_errors(tmp_path, monkeypatch):
    _setup_project_with_prompt(tmp_path, monkeypatch)
    r = runner.invoke(app, ["eval", "--project", "demo", "--split", "dev"])
    assert r.exit_code != 0  # empty dev split
