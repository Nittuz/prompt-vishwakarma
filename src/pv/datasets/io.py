"""Load, write, validate, and summarize JSONL datasets."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .model import Example


def load_jsonl(path: Path) -> list[Example]:
    path = Path(path)
    if not path.exists():
        return []
    out: list[Example] = []
    for i, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            out.append(Example(**json.loads(line)))
        except Exception as e:
            raise ValueError(f"{path}:{i}: {e}")
    return out


def write_jsonl(path: Path, examples: list[Example]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(e.model_dump_json() for e in examples)
    path.write_text(body + ("\n" if examples else ""))


def append_jsonl(path: Path, examples: list[Example]) -> None:
    existing = load_jsonl(path)
    write_jsonl(path, existing + examples)


def validate(examples: list[Example], required_inputs: list[str] | None = None) -> list[str]:
    problems: list[str] = []
    dups = [k for k, c in Counter(e.id for e in examples).items() if c > 1]
    if dups:
        problems.append(f"duplicate ids: {dups}")
    for e in examples:
        for field in required_inputs or []:
            if field not in e.input:
                problems.append(f"{e.id}: missing input field {field!r}")
    return problems


def stats(examples: list[Example]) -> dict:
    field_counts = Counter(k for e in examples for k in e.input)
    return {
        "count": len(examples),
        "with_reference": sum(1 for e in examples if e.reference is not None),
        "input_fields": dict(field_counts),
    }
