"""A runner wrapper that accumulates cost/usage across calls."""

from __future__ import annotations

from .base import GenParams, Message, Response, Runner


class MeteringRunner:
    def __init__(self, inner: Runner):
        self.inner = inner
        self.name = inner.name
        self.total_cost: float = 0.0
        self.n_calls: int = 0

    def complete(self, messages: list[Message], params: GenParams) -> Response:
        resp = self.inner.complete(messages, params)
        self.total_cost += resp.usage.cost_usd
        self.n_calls += 1
        return resp
