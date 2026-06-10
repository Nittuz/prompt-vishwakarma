"""A deterministic, offline runner for tests and `PV_RUNNER=fake`.

With no responder supplied it echoes text, or fills a JSON-schema-shaped stub so
the generate/critique/repo-analysis flows produce meaningful output offline.
"""

from __future__ import annotations

import json
from typing import Callable

from .base import GenParams, Message, Response, Usage


def fill_schema(schema: dict) -> dict:
    """Return a dict satisfying a simple JSON schema's properties."""
    props = schema.get("properties", {})
    required = schema.get("required") or list(props)
    out: dict = {}
    for name in required:
        spec = props.get(name, {})
        kind = spec.get("type", "string")
        if kind == "string":
            out[name] = f"fake {name}"
        elif kind == "array":
            out[name] = []
        elif kind == "object":
            out[name] = {}
        elif kind in ("integer", "number"):
            out[name] = 0
        elif kind == "boolean":
            out[name] = False
        else:
            out[name] = None
    return out


class FakeRunner:
    name = "fake"

    def __init__(self, responder: Callable[[list[Message], GenParams], object] | None = None):
        # responder(messages, params) -> str | dict
        self.responder = responder
        self.calls: list[tuple[list[Message], GenParams]] = []

    def complete(self, messages: list[Message], params: GenParams) -> Response:
        self.calls.append((messages, params))
        if self.responder is not None:
            out = self.responder(messages, params)
        elif params.json_schema is not None:
            out = fill_schema(params.json_schema)
        else:
            out = "FAKE: " + (messages[-1].content if messages else "")

        if isinstance(out, dict):
            return Response(
                text=json.dumps(out),
                structured=out,
                usage=Usage(cost_usd=0.0),
                model=params.model,
            )
        return Response(text=str(out), usage=Usage(cost_usd=0.0), model=params.model)
