from pv.store.runs import RunStore


def test_record_and_total(tmp_path):
    s = RunStore(tmp_path / "runs.db")
    s.record("generate", "agenda", model="opus", cost_usd=0.02)
    s.record("generate", "review", model="opus", cost_usd=0.03)
    assert round(s.total_cost(), 2) == 0.05
    rows = s.list()
    assert len(rows) == 2
    assert rows[0][2] == "review"  # newest first


def test_empty_total(tmp_path):
    assert RunStore(tmp_path / "runs.db").total_cost() == 0
