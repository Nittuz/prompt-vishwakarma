"""Runner selection. `PV_RUNNER=fake` forces the offline engine everywhere."""

from __future__ import annotations

import os

from .base import Runner
from .claude_runner import ClaudeRunner
from .fake_runner import FakeRunner


def get_runner(name: str = "claude") -> Runner:
    if os.getenv("PV_RUNNER") == "fake" or name == "fake":
        return FakeRunner()
    if name == "claude":
        return ClaudeRunner()
    raise ValueError(f"unknown runner: {name!r}")
