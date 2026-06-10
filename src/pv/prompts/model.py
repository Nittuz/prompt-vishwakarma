"""The PromptVersion model: a versioned, renderable prompt template."""

from __future__ import annotations

import hashlib
import re

from pydantic import BaseModel, Field

# A variable is exactly ``{word}``. JSON braces like ``{"k": 1}`` won't match.
_VAR = re.compile(r"{(\w+)}")


class PromptVersion(BaseModel):
    name: str
    version: int = 1
    role: str | None = None
    description: str = ""
    defaults: dict = Field(default_factory=dict)
    system: str = ""
    user: str = ""

    @property
    def content_hash(self) -> str:
        blob = f"{self.system}\x00{self.user}\x00{sorted(self.defaults.items())}"
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    def variables(self) -> set[str]:
        return set(_VAR.findall(self.system)) | set(_VAR.findall(self.user))

    def render(self, variables: dict) -> tuple[str, str]:
        """Return (system, user) with ``{var}`` placeholders substituted.

        Substitutes only known ``{word}`` placeholders, leaving any other braces
        (e.g. JSON examples) untouched. Raises ``KeyError`` for missing vars.
        """
        missing = self.variables() - set(variables)
        if missing:
            raise KeyError(f"missing variables: {sorted(missing)}")

        def sub(text: str) -> str:
            return _VAR.sub(
                lambda m: str(variables[m.group(1)])
                if m.group(1) in variables
                else m.group(0),
                text,
            )

        return sub(self.system), sub(self.user)
