import pytest

from pv.roles.model import list_roles, load_role


def test_builtins_present():
    names = list_roles()
    for r in ["meeting", "feature_design", "code_review", "general", "writer", "extract"]:
        assert r in names


def test_load_role_fields():
    r = load_role("code_review")
    assert r.repo_analysis in ("off", "light", "deep")
    assert r.sections and r.checklist and r.playbook
    assert "json_schema_valid" in r.scorers


def test_unknown_role_raises():
    with pytest.raises(FileNotFoundError):
        load_role("does_not_exist")
