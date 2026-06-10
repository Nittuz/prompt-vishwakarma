"""A runner wrapper that serves repeated identical calls from a local cache.

Conserves the Agent-SDK credit pool: a cache hit costs $0 (the stored cost is
zeroed so the meter reflects only real spend this run).
"""

from __future__ import annotations

from .base import GenParams, Message, Response, Runner
from .cache import ResponseCache


class CachingRunner:
    def __init__(self, inner: Runner, cache: ResponseCache):
        self.inner = inner
        self.cache = cache
        self.name = inner.name

    def _key(self, messages: list[Message], params: GenParams) -> str:
        return self.cache.key(
            messages=[(m.role, m.content) for m in messages],
            model=params.model,
            system=params.system,
            schema=params.json_schema,
            tools=sorted(params.tools),
            add_dir=params.add_dir,
        )

    def complete(self, messages: list[Message], params: GenParams) -> Response:
        key = self._key(messages, params)
        hit = self.cache.get(key)
        if hit is not None:
            # No new spend on a hit — zero the cost the meter will see.
            return hit.model_copy(
                update={"usage": hit.usage.model_copy(update={"cost_usd": 0.0})}
            )
        resp = self.inner.complete(messages, params)
        self.cache.put(key, resp)
        return resp
