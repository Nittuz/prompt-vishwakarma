"""Content-addressed cache of runner responses (conserves the credit pool)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .base import Response


class ResponseCache:
    def __init__(self, directory: Path):
        self.dir = Path(directory)
        self.dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key(**parts) -> str:
        blob = json.dumps(parts, sort_keys=True, default=str)
        return hashlib.sha256(blob.encode()).hexdigest()

    def _path(self, key: str) -> Path:
        return self.dir / f"{key}.json"

    def get(self, key: str) -> Response | None:
        path = self._path(key)
        if not path.exists():
            return None
        try:
            return Response.model_validate_json(path.read_text())
        except Exception:
            return None

    def put(self, key: str, response: Response) -> None:
        self._path(key).write_text(response.model_dump_json())
