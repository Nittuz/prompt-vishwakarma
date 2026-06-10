"""Runner protocol and the message/params/response data model."""

from __future__ import annotations

from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class GenParams(BaseModel):
    model: str = "opus"
    max_tokens: int = 4096
    system: str | None = None
    json_schema: dict | None = None
    budget_usd: float | None = None
    # [] → pure text mode (no tools). e.g. ["Read", "Glob", "Grep"] for repo scans.
    tools: list[str] = Field(default_factory=list)


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class Response(BaseModel):
    text: str
    structured: dict | None = None
    usage: Usage = Field(default_factory=Usage)
    latency_ms: int = 0
    model: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)


@runtime_checkable
class Runner(Protocol):
    name: str

    def complete(self, messages: list[Message], params: GenParams) -> Response:
        ...
