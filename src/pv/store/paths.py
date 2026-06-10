"""Filesystem path resolution for a Prompt Vishwakarma workspace.

The "repo root" is the nearest ancestor containing a ``pyproject.toml`` (so the
toolkit works whether invoked from the repo root or a subdirectory); it falls
back to the current working directory when none is found.
"""

from __future__ import annotations

from pathlib import Path


def repo_root(start: Path | None = None) -> Path:
    """Nearest ancestor containing ``pyproject.toml``, else ``start``/cwd."""
    start = Path(start) if start else Path.cwd()
    start = start.resolve()
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").exists():
            return candidate
    return start


def library_dir(root: Path) -> Path:
    return Path(root) / "library"


def projects_dir(root: Path) -> Path:
    return Path(root) / "projects"


def cache_dir(root: Path) -> Path:
    return Path(root) / ".pv" / "cache"


def runs_db(root: Path) -> Path:
    return Path(root) / ".pv" / "runs.db"


def ensure(path: Path) -> Path:
    """Create ``path`` as a directory (with parents) and return it."""
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path
