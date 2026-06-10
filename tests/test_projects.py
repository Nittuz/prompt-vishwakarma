import pytest

from pv.projects import store
from pv.projects.model import Project
from pv.prompts.model import PromptVersion
from pv.prompts.registry import PromptStore
from pv.store import paths


def test_init_creates_structure(tmp_path):
    p = store.init_project(tmp_path, "demo", role="extract")
    assert p.role == "extract"
    assert store.project_file(tmp_path, "demo").exists()
    # extract role's scorers seeded
    assert "json_schema_valid" in p.scorers
    for split in ("train", "dev", "test"):
        assert store.dataset_path(tmp_path, p, split).exists()


def test_load_roundtrip(tmp_path):
    store.init_project(tmp_path, "demo", role="general")
    loaded = store.load_project(tmp_path, "demo")
    assert loaded.name == "demo"
    assert loaded.models["judge"] == "opus"


def test_load_missing_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        store.load_project(tmp_path, "nope")


def test_promote_copies_library_prompt(tmp_path):
    lib = PromptStore(paths.library_dir(tmp_path))
    lib.save_new_version(PromptVersion(name="agenda", role="meeting", system="s", user="u {x}"))
    project = store.promote(tmp_path, "agenda", to_project="mbr")
    assert project.name == "mbr"
    assert store.exists(tmp_path, "mbr")
    copied = store.prompt_store_for(tmp_path, "mbr").load("agenda")
    assert copied.system == "s" and copied.role == "meeting"
