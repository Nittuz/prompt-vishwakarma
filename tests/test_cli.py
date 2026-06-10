from typer.testing import CliRunner

from pv.cli import app

runner = CliRunner()


def _mark_root(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")


def test_new_generates_into_library(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PV_RUNNER", "fake")
    _mark_root(tmp_path)
    r = runner.invoke(app, ["new", "Build an MBR agenda", "--role", "meeting", "--no-analyze"])
    assert r.exit_code == 0, r.output
    libs = list((tmp_path / "library").glob("*/v1.yaml"))
    assert libs, r.output
    assert "generated" in r.output


def test_new_with_target_exports(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PV_RUNNER", "fake")
    _mark_root(tmp_path)
    r = runner.invoke(
        app,
        ["new", "review changes", "--role", "code_review", "--no-analyze", "--target", "claude"],
    )
    assert r.exit_code == 0, r.output
    skills = list((tmp_path / "library").rglob("SKILL.md"))
    assert skills, r.output


def test_critique_adds_version(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PV_RUNNER", "fake")
    _mark_root(tmp_path)
    runner.invoke(app, ["new", "agenda thing", "--role", "meeting", "--no-analyze"])
    name = next((tmp_path / "library").iterdir()).name
    r = runner.invoke(app, ["prompt", "critique", name])
    assert r.exit_code == 0, r.output
    versions = sorted((tmp_path / "library" / name).glob("v*.yaml"))
    assert len(versions) == 2


def test_role_list_and_show():
    r = runner.invoke(app, ["role", "list"])
    assert r.exit_code == 0 and "meeting" in r.output
    r2 = runner.invoke(app, ["role", "show", "code_review"])
    assert r2.exit_code == 0 and "checklist" in r2.output


def test_stub_exits_cleanly(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _mark_root(tmp_path)
    r = runner.invoke(app, ["optimize", "--project", "x"])
    assert r.exit_code == 0 and "coming in" in r.output
