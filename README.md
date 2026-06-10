# Prompt Vishwakarma (`pv`)

A **local-first toolkit for generating and improving prompts** using only the
tools you already have — **Claude Code**, **Cursor**, and the **ChatGPT
website**. **No API key required to start:** the engine is Claude Code itself,
run key-free via the `claude` CLI in headless mode.

> Status: Phases 1–3 (Generate front door + the Improve path: eval / scorers /
> LLM-judge). Optimize / distill are planned follow-ups — see
> `docs/superpowers/specs/` and `docs/superpowers/plans/`.

## Install

```bash
python3 -m pip install -e ".[dev]"
```

## The front door: `pv new`

Give a brief (idea + role, optionally a repo) → get a versioned, ready-to-use
prompt in `library/`:

```bash
# Meeting agenda (no repo)
pv new "agenda for my monthly business review meeting" --role meeting

# Repo-aware feature design → export as a Cursor rule
pv new "design a feature reusing existing code" \
  --role feature_design --repo ~/code/myapp --target cursor

# Repo-aware legacy review → export as a Claude Code skill
pv new "review changes in our legacy repo" \
  --role code_review --repo ~/code/legacy --target claude
```

Then optionally sharpen it:

```bash
pv prompt critique <name>          # single-shot improvement → new version
pv export <name> --target chatgpt  # emit a portable artifact
pv runs list                       # see runs + cumulative cost
```

### Roles

`meeting`, `feature_design`, `code_review`, `general`, `writer`, `extract`.
Each is a *prompt-category playbook* (generation scaffold + eval defaults).
`pv role list` / `pv role show <name>`.

### Repo-aware generation (toggle)

For `--repo` tasks: light analysis by default, `--deep` for thorough,
`--no-analyze` to skip (the generated prompt then tells the downstream agent to
inspect the repo at use-time).

## Improve path (Phase 3)

When a prompt matters enough to harden, graduate it into a **project** and
measure it over a dataset:

```bash
pv promote <library-prompt> --to-project myproj   # or: pv init myproj --role <role>
# add cases to projects/myproj/datasets/dev.jsonl (one JSON Example per line),
# or synthesize seeds with Claude (curate after):
pv data gen --project myproj --n 10 --split dev
pv data validate --project myproj --split dev
pv data stats --project myproj --split dev

pv eval --project myproj --split dev [--model haiku] [--budget-usd 1.0]
pv runs compare <run_id_a> <run_id_b>
```

`pv eval` runs the project's prompt over the split with the configured
**scorers** (`exact_match`, `contains`, `regex`, `json_schema_valid`,
`numeric_tolerance`, and `llm_judge`), writing a Markdown report and a ledger
entry. **Scorers** and **models** live in `projects/<name>/project.yaml`; the
`llm_judge` defaults to **opus** (set `models.judge: haiku` to cut cost on large
dev sets). An `Example` is `{"id": "...", "input": {...}, "reference": ...}`.

## Engine: live vs offline

- **Live (default):** uses the `claude` CLI in headless mode — reuses your
  Claude Code auth, **no API key**. ⚠️ On subscription plans, headless usage
  draws from a monthly Agent-SDK credit pool; outputs are cached and every run
  records its cost (`pv runs list`).
- **Offline / CI:** `export PV_RUNNER=fake` uses a deterministic fake engine so
  the CLI and tests run with zero model calls.

**Auth:** works with whatever your Claude Code uses — OAuth/subscription login,
API key, or a 3rd-party provider (Vertex/Bedrock). When an API-key or 3P-provider
credential is present, runs use `--bare` (skips hooks/`CLAUDE.md` for cheaper,
unbiased generation). Pure OAuth/subscription users automatically run without
`--bare` so login still works. Identical repeated calls are served from a local
cache (`--no-cache` to bypass).

### v1 notes
- `pv new` builds the brief from the **idea + role** (and `--repo`). Richer brief
  fields (audience, explicit inputs/constraints) are a planned enhancement — for
  now, fold them into the idea text.
- The engine calls the `claude` CLI via subprocess. The official Claude Agent SDK
  is a planned drop-in behind the same `Runner` interface.

## Develop

```bash
pytest
```
