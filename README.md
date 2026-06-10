# Prompt Vishwakarma (`pv`)

A **local-first toolkit for generating and improving prompts** using only the
tools you already have — **Claude Code**, **Cursor**, and the **ChatGPT
website**. **No API key required to start:** the engine is Claude Code itself,
run key-free via the `claude` CLI in headless mode.

> Status: Phases 1–2 (foundations + the Generate front door). Eval / optimize /
> distill are planned follow-ups — see `docs/superpowers/specs/` and
> `docs/superpowers/plans/`.

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

## Engine: live vs offline

- **Live (default):** uses the `claude` CLI in headless mode — reuses your
  Claude Code auth, **no API key**. ⚠️ On subscription plans, headless usage
  draws from a monthly Agent-SDK credit pool; outputs are cached and every run
  records its cost (`pv runs list`).
- **Offline / CI:** `export PV_RUNNER=fake` uses a deterministic fake engine so
  the CLI and tests run with zero model calls.

> Implementation note: v1 calls the `claude` CLI via subprocess. The official
> Claude Agent SDK is a planned drop-in behind the same `Runner` interface.

## Develop

```bash
pytest
```
