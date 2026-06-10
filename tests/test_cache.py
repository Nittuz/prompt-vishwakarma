from pv.runners.cache import ResponseCache
from pv.runners.base import Response, Usage


def test_cache_roundtrip(tmp_path):
    c = ResponseCache(tmp_path)
    key = c.key(prompt="hi", model="opus", extra={"schema": None})
    assert c.get(key) is None
    r = Response(text="ok", usage=Usage(cost_usd=0.01), model="opus")
    c.put(key, r)
    got = c.get(key)
    assert got is not None
    assert got.text == "ok"
    assert got.usage.cost_usd == 0.01


def test_cache_key_is_stable_and_order_independent():
    c = ResponseCache.key
    assert c(a=1, b=2) == c(b=2, a=1)
    assert c(a=1) != c(a=2)
