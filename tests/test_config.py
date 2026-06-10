from pv.config import resolve_model, MODEL_ALIASES, estimate_cost
from pv.store import paths


def test_model_alias_resolution():
    assert resolve_model("opus") == MODEL_ALIASES["opus"] == "claude-opus-4-8"
    assert resolve_model("claude-opus-4-8") == "claude-opus-4-8"  # passthrough
    assert resolve_model("something-custom") == "something-custom"


def test_estimate_cost_known_and_unknown():
    # opus = $5 / $25 per MTok
    assert estimate_cost("opus", 1_000_000, 0) == 5.0
    assert estimate_cost("opus", 0, 1_000_000) == 25.0
    assert estimate_cost("mystery-model", 1_000_000, 1_000_000) == 0.0


def test_paths_under_root(tmp_path):
    root = paths.repo_root(start=tmp_path)
    assert paths.library_dir(root).name == "library"
    assert paths.cache_dir(root).parts[-2:] == (".pv", "cache")
    assert paths.runs_db(root).parts[-2:] == (".pv", "runs.db")


def test_repo_root_finds_pyproject(tmp_path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    sub = tmp_path / "a" / "b"
    sub.mkdir(parents=True)
    assert paths.repo_root(start=sub) == tmp_path.resolve()
