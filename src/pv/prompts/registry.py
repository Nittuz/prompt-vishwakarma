"""File-backed prompt store over ``<base>/<name>/vN.yaml``."""

from __future__ import annotations

from pathlib import Path

import yaml

from .model import PromptVersion

_BODY_FIELDS = ("role", "description", "defaults", "system", "user")


class PromptStore:
    def __init__(self, base: Path):
        self.base = Path(base)
        self.base.mkdir(parents=True, exist_ok=True)

    def _dir(self, name: str) -> Path:
        return self.base / name

    def versions(self, name: str) -> list[int]:
        d = self._dir(name)
        if not d.exists():
            return []
        return sorted(int(p.stem[1:]) for p in d.glob("v*.yaml") if p.stem[1:].isdigit())

    def load(self, name: str, version: int | None = None) -> PromptVersion:
        vs = self.versions(name)
        if not vs:
            raise FileNotFoundError(f"no prompt named {name!r}")
        v = version or vs[-1]
        if v not in vs:
            raise FileNotFoundError(f"{name} has no version {v}")
        data = yaml.safe_load((self._dir(name) / f"v{v}.yaml").read_text()) or {}
        return PromptVersion(name=name, version=v, **data)

    def save_new_version(self, prompt: PromptVersion) -> PromptVersion:
        d = self._dir(prompt.name)
        d.mkdir(parents=True, exist_ok=True)
        existing = self.versions(prompt.name)
        nextv = (existing[-1] + 1) if existing else 1
        saved = prompt.model_copy(update={"version": nextv})
        body = {k: getattr(saved, k) for k in _BODY_FIELDS}
        (d / f"v{nextv}.yaml").write_text(yaml.safe_dump(body, sort_keys=False))
        return saved

    def list(self) -> list[str]:
        if not self.base.exists():
            return []
        return sorted(d.name for d in self.base.iterdir() if d.is_dir())
