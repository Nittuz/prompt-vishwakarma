"""Project filesystem operations: load/save, init, promote."""

from __future__ import annotations

from pathlib import Path

import yaml

from ..prompts.registry import PromptStore
from ..roles.model import load_role
from ..store import paths
from .model import Project


def project_dir(root: Path, name: str) -> Path:
    return paths.projects_dir(root) / name


def project_file(root: Path, name: str) -> Path:
    return project_dir(root, name) / "project.yaml"


def exists(root: Path, name: str) -> bool:
    return project_file(root, name).exists()


def load_project(root: Path, name: str) -> Project:
    f = project_file(root, name)
    if not f.exists():
        raise FileNotFoundError(f"no project named {name!r}")
    return Project(name=name, **(yaml.safe_load(f.read_text()) or {}))


def save_project(root: Path, project: Project) -> None:
    d = project_dir(root, project.name)
    d.mkdir(parents=True, exist_ok=True)
    body = project.model_dump(exclude={"name"})
    project_file(root, project.name).write_text(yaml.safe_dump(body, sort_keys=False))


def prompt_store_for(root: Path, name: str) -> PromptStore:
    return PromptStore(project_dir(root, name) / "prompts")


def dataset_path(root: Path, project: Project, split: str) -> Path:
    if split not in project.datasets:
        raise KeyError(f"unknown split {split!r} (have {sorted(project.datasets)})")
    return project_dir(root, project.name) / project.datasets[split]


def init_project(root: Path, name: str, role: str) -> Project:
    role_obj = load_role(role)
    project = Project(name=name, role=role, scorers=role_obj.scorers or ["llm_judge"])
    d = project_dir(root, name)
    (d / "datasets").mkdir(parents=True, exist_ok=True)
    for split in project.datasets:
        p = dataset_path(root, project, split)
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("")
    save_project(root, project)
    (d / "README.md").write_text(f"# {name}\n\nRole: {role}. Created by `pv init`.\n")
    return project


def promote(root: Path, prompt_name: str, to_project: str) -> Project:
    """Copy a library prompt (latest) into a project, creating it if needed."""
    lib = PromptStore(paths.library_dir(root))
    prompt = lib.load(prompt_name)  # raises FileNotFoundError if absent
    role = prompt.role or "general"
    project = load_project(root, to_project) if exists(root, to_project) else init_project(
        root, to_project, role
    )
    prompt_store_for(root, to_project).save_new_version(prompt.model_copy(update={"version": 1}))
    return project
