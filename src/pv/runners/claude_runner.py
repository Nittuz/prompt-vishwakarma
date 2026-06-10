"""The default engine: the `claude` CLI in headless mode (no API key).

Reuses the user's existing Claude Code auth (OAuth / keychain / 3P provider).
`build_command` and `parse` are pure functions so they can be tested without
invoking the binary.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time

from ..config import estimate_cost, resolve_model
from .base import GenParams, Message, Response, Usage

DEFAULT_TIMEOUT_S = 300

# Env that indicates an auth path `--bare` supports (API key or a 3P provider).
# `--bare` reads ONLY these — never OAuth/keychain — so we add it only when one
# is present; pure OAuth/subscription users must run without `--bare`.
_BARE_SAFE_ENV = (
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "CLAUDE_CODE_USE_VERTEX",
    "CLAUDE_CODE_USE_BEDROCK",
)


def _bare_is_safe() -> bool:
    return any(os.getenv(v) for v in _BARE_SAFE_ENV)


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
            "--model",
            resolve_model(params.model),
        ]
        # `--bare` (skip hooks/CLAUDE.md/plugins → cheaper, unbiased, reproducible)
        # forces auth to API-key/3P-provider only — OAuth & keychain are NOT read.
        # Add it only when such auth is present; pure OAuth users run without it.
        if _bare_is_safe():
            cmd.append("--bare")
        if params.add_dir:
            cmd += ["--add-dir", params.add_dir]
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
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            raise RuntimeError(f"claude returned non-JSON output: {stdout[:500]!r}")
        usage = data.get("usage") or {}
        model_usage = data.get("modelUsage") or {}
        model = next(iter(model_usage), "").split("@")[0]  # strip @<date> suffix
        in_tok = usage.get("input_tokens", 0)
        out_tok = usage.get("output_tokens", 0)
        cost = data.get("total_cost_usd")
        if cost is None:  # fall back to a best-effort estimate
            cost = estimate_cost(model, in_tok, out_tok)
        return Response(
            text=data.get("result", ""),
            structured=data.get("structured_output"),
            usage=Usage(input_tokens=in_tok, output_tokens=out_tok, cost_usd=cost),
            model=model,
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
        timeout_s = int(os.getenv("PV_TIMEOUT", DEFAULT_TIMEOUT_S))
        # For pure generation (no repo), run from a neutral dir so the engine
        # doesn't autodiscover the caller's project CLAUDE.md/hooks (cost + bias).
        # Repo-analysis calls run from the repo so its file tools can read it.
        cwd = params.add_dir or tempfile.gettempdir()
        t0 = time.time()
        try:
            proc = subprocess.run(
                cmd,
                input=self.render_stdin(messages),
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError(
                f"claude timed out after {timeout_s}s (set PV_TIMEOUT to adjust)."
            )
        if proc.returncode != 0:
            detail = (proc.stderr or "").strip() or (proc.stdout or "").strip()
            raise RuntimeError(f"claude failed (exit {proc.returncode}): {detail[:500]}")
        resp = self.parse(proc.stdout)
        resp.latency_ms = int((time.time() - t0) * 1000)
        return resp
