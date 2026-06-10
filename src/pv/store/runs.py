"""A minimal SQLite ledger of runs, primarily for cost visibility."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

_DDL = """
CREATE TABLE IF NOT EXISTS runs(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL,
    kind TEXT,
    name TEXT,
    model TEXT,
    cost_usd REAL,
    detail TEXT
)
"""


class RunStore:
    def __init__(self, db_path: Path):
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path)
        self.db.execute(_DDL)
        self.db.commit()

    def record(
        self,
        kind: str,
        name: str,
        model: str = "",
        cost_usd: float = 0.0,
        detail: dict | None = None,
    ) -> int:
        cur = self.db.execute(
            "INSERT INTO runs(ts, kind, name, model, cost_usd, detail) VALUES(?,?,?,?,?,?)",
            (time.time(), kind, name, model, cost_usd, json.dumps(detail or {})),
        )
        self.db.commit()
        return cur.lastrowid

    def list(self, limit: int = 50) -> list[tuple]:
        return self.db.execute(
            "SELECT id, kind, name, model, cost_usd FROM runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()

    def total_cost(self) -> float:
        return self.db.execute("SELECT COALESCE(SUM(cost_usd), 0) FROM runs").fetchone()[0]

    def close(self) -> None:
        self.db.close()
