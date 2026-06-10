from pv.runners.base import GenParams, Message, Response, Usage
from pv.runners.cache import ResponseCache
from pv.runners.caching import CachingRunner


class _Counter:
    name = "counter"

    def __init__(self):
        self.n = 0

    def complete(self, messages, params):
        self.n += 1
        return Response(text="real", usage=Usage(cost_usd=0.05), model="opus")


def test_cache_hit_is_free_and_skips_inner(tmp_path):
    inner = _Counter()
    r = CachingRunner(inner, ResponseCache(tmp_path))
    msgs = [Message(role="user", content="hi")]
    p = GenParams()

    a = r.complete(msgs, p)
    assert inner.n == 1
    assert a.usage.cost_usd == 0.05  # first call: real spend

    b = r.complete(msgs, p)
    assert inner.n == 1  # served from cache, inner not called again
    assert b.usage.cost_usd == 0.0  # cache hit: no new spend
    assert b.text == "real"


def test_distinct_inputs_miss(tmp_path):
    inner = _Counter()
    r = CachingRunner(inner, ResponseCache(tmp_path))
    r.complete([Message(role="user", content="a")], GenParams())
    r.complete([Message(role="user", content="b")], GenParams())
    assert inner.n == 2
