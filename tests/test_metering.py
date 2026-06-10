from pv.runners.base import GenParams, Message, Response, Usage
from pv.runners.metering import MeteringRunner


class _Stub:
    name = "stub"

    def complete(self, messages, params):
        return Response(text="x", usage=Usage(cost_usd=0.01))


def test_metering_accumulates():
    m = MeteringRunner(_Stub())
    m.complete([Message(role="user", content="a")], GenParams())
    m.complete([Message(role="user", content="b")], GenParams())
    assert round(m.total_cost, 2) == 0.02
    assert m.n_calls == 2
    assert m.name == "stub"
