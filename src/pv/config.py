"""Settings, model aliases, and a best-effort cost table.

No API key is required to run `pv`; `.env` loading exists only for future
optional integrations (e.g. an OpenAI runner).
"""

from __future__ import annotations

try:  # optional convenience; never required
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is a soft dependency
    pass

# Friendly aliases the `claude` CLI accepts, mapped to canonical model ids.
MODEL_ALIASES: dict[str, str] = {
    "opus": "claude-opus-4-8",
    "sonnet": "claude-sonnet-4-6",
    "haiku": "claude-haiku-4-5",
    "fable": "claude-fable-5",
}

# Best-effort fallback pricing (USD per 1M tokens). Only used to *estimate* cost
# when the runner does not report `total_cost_usd`; the runner's number wins.
COST_PER_MTOK: dict[str, tuple[float, float]] = {
    "claude-opus-4-8": (5.0, 25.0),
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-fable-5": (10.0, 50.0),
}


def resolve_model(model: str) -> str:
    """Map an alias to its canonical id; pass through anything else unchanged."""
    return MODEL_ALIASES.get(model, model)


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Fallback cost estimate when the runner reports none."""
    rate = COST_PER_MTOK.get(resolve_model(model))
    if not rate:
        return 0.0
    in_rate, out_rate = rate
    return (input_tokens * in_rate + output_tokens * out_rate) / 1_000_000
