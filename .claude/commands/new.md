---
description: Generate a new prompt from a brief (idea + role, optional repo) via `pv new`.
---

The user wants to generate a prompt. Gather a short brief, then run the `pv`
CLI to generate it.

1. Ask only for what's missing: the core **idea**, a **role** (one of:
   `meeting`, `feature_design`, `code_review`, `general`, `writer`, `extract`;
   run `pv role list` if unsure), and — for repo-aware roles — the **repo path**.
2. Run it (use the project's venv if present, e.g. `.venv/bin/pv`):

   `pv new "<idea>" --role <role> [--repo <path>] [--deep|--no-analyze] [--target claude|cursor|chatgpt]`

3. Show the user the generated prompt path under `library/<name>/` and the
   printed rationale + cost. Offer `pv prompt critique <name>` to sharpen it, or
   `pv export <name> --target <t>` to emit an artifact.

Arguments: $ARGUMENTS
