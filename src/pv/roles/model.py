"""Role model + loaders over the built-in YAML playbooks."""

from __future__ import annotations

from importlib import resources

import yaml
from pydantic import BaseModel, Field

_ANCHOR = "pv.roles.builtin"


class Role(BaseModel):
    name: str
    description: str = ""
    sections: list[str] = Field(default_factory=list)  # required prompt sections
    checklist: list[str] = Field(default_factory=list)  # generator best-practices
    repo_analysis: str = "off"  # off | light | deep (default for this role)
    target: str = "raw"  # default export target
    scorers: list[str] = Field(default_factory=list)  # eval defaults (later phases)
    playbook: list[str] = Field(default_factory=list)


def list_roles() -> list[str]:
    return sorted(
        p.name[:-5]
        for p in resources.files(_ANCHOR).iterdir()
        if p.name.endswith(".yaml")
    )


def load_role(name: str) -> Role:
    resource = resources.files(_ANCHOR) / f"{name}.yaml"
    if not resource.is_file():
        raise FileNotFoundError(f"unknown role: {name!r} (have {list_roles()})")
    data = yaml.safe_load(resource.read_text()) or {}
    return Role(name=name, **data)
