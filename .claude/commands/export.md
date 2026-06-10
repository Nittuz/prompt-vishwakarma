---
description: Export a library prompt to a Claude skill / Cursor rule / ChatGPT GPT via `pv export`.
---

The user wants to export a prompt into a usable artifact.

1. If no name is given, run `pv prompt list` and ask which one.
2. Ask the target if not given: `claude` (Claude Code skill), `cursor` (Cursor rule), or `chatgpt` (Custom GPT spec).
3. Run: `pv export <name> --target <target>` (use `.venv/bin/pv` if the project venv exists).
4. Show the output path and, for `chatgpt`, remind the user to paste the spec into ChatGPT → Create a GPT.

Arguments: $ARGUMENTS
