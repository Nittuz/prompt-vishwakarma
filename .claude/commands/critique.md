---
description: Critique and improve an existing library prompt via `pv prompt critique`.
---

The user wants to improve an existing prompt.

1. If no name is given, run `pv prompt list` and ask which one.
2. Run: `pv prompt critique <name>` (use `.venv/bin/pv` if the project venv exists).
3. Report the summary of changes and the new version number; offer `pv prompt diff <name> <v1> <v2>` to show the delta.

Arguments: $ARGUMENTS
