"""The default engine: the `claude` CLI in headless mode (no API key).

Reuses the user's existing Claude Code auth. `build_command` and `parse` are
pure functions so they can be tested without invoking the binary.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time

from ..config import resolve_model
from .base import GenParams, Message, Response, Usage


class ClaudeRunner:
    name = "claude"

    def __init__(self, binary: str = "claude"):
        self.binary = binary

    def build_command(self, params: GenParams) -> list[str]:
        cmd = [
            self.binary,
            "-p",
            "--output-format",
            "json",
            "--bare",
            "--model",
            resolve_model(params.model),
        ]
        if params.tools:
            cmd += ["--allowedTools", ",".join(params.tools)]
        else:
            cmd += ["--tools", ""]  # pure text-in/text-out, no agentic tools
        if params.system:
            cmd += ["--append-system-prompt", params.system]
        if params.json_schema is not None:
            cmd += ["--json-schema", json.dumps(params.json_schema)]
        if params.budget_usd is not None:
            cmd += ["--max-budget-usd", str(params.budget_usd)]
        return cmd

    @staticmethod
    def render_stdin(messages: list[Message]) -> str:
        # System turns are passed via --append-system-prompt; join the rest.
        return "\n\n".join(m.content for m in messages if m.role != "system")

    @staticmethod
    def parse(stdout: str) -> Response:
        data = json.loads(stdout)
        usage = data.get("usage") or {}
        model_usage = data.get("modelUsage") or {}
        return Response(
            text=data.get("result", ""),
            structured=data.get("structured_output"),
            usage=Usage(
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                cost_usd=data.get("total_cost_usd", 0.0),
            ),
            model=next(iter(model_usage), ""),
            raw=data,
        )

    def complete(self, messages: list[Message], params: GenParams) -> Response:
        if shutil.which(self.binary) is None:
            raise RuntimeError(
                f"'{self.binary}' not found on PATH. The claude runner needs the "
                "Claude Code CLI. Set PV_RUNNER=fake for offline use."
            )
        # Fold any system messages into params.system if not already set.
        sys_msgs = [m.content for m in messages if m.role == "system"]
        if sys_msgs and not params.system:
            params = params.model_copy(update={"system": "\n\n".join(sys_msgs)})

        cmd = self.build_command(params)
        t0 = time.time()
        proc = subprocess.run(
            cmd,
            input=self.render_stdin(messages),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"claude failed (exit {proc.returncode}): {proc.stderr[:500]}"
            )
        resp = self.parse(proc.stdout)
        resp.latency_ms = int((time.time() - t0) * 1000)
        return resp
