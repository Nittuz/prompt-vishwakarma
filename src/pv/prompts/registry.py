"""File-backed prompt store over ``<base>/<name>/vN.yaml``."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import yaml

from .model import PromptVersion

_BODY_FIELDS = ("role", "description", "defaults", "system", "user")


def _validate_name(name: str) -> str:
    """Reject names that could escape the store directory."""
    if not name or "/" in name or "\\" in name or name in (".", "..") or ".." in name:
        raise ValueError(f"invalid prompt name: {name!r}")
    return name


class PromptStore:
    def __init__(self, base: Path):
        self.base = Path(base)
        self.base.mkdir(parents=True, exist_ok=True)

    def _dir(self, name: str) -> Path:
        return self.base / _validate_name(name)

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
        _atomic_write(d / f"v{nextv}.yaml", yaml.safe_dump(body, sort_keys=False))
        return saved

    def list(self) -> list[str]:
        if not self.base.exists():
            return []
        return sorted(d.name for d in self.base.iterdir() if d.is_dir())


def _atomic_write(path: Path, content: str) -> None:
    """Write via a temp file + atomic rename so an interrupt can't corrupt it."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(content)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)
