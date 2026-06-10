# Prompt Vishwakarma — Design Spec

- **Date:** 2026-06-10
- **Repo:** `prompt-vishwakarma` (https://github.com/Nittuz/prompt-vishwakarma.git)
- **Package / CLI:** `pv`
- **Status:** Approved design — ready for implementation planning

---

## 1. Purpose

A **local-first toolkit for generating and improving prompts, and producing
"fine-tunes,"** using only the tools the author already has — **Claude Code**,
**Cursor**, and the **ChatGPT website** — with **no API key required to start**.

### Two modes (the primary mental model)

1. **Generate (fast path) — the front door.** Give a **brief** (core idea +
   workflow + role, optionally a repo) → the tool generates a strong,
   ready-to-use prompt. No dataset needed. This is the most common use.
2. **Improve (rigorous path).** Once you have a few examples, evaluate →
   optimize → distill → export to systematically harden a prompt. You graduate
   into this only when it's worth it.

The full flywheel:

> **brief → generate prompt** (role + optional repo analysis) → use it / export it
> → *(optional)* evaluate → optimize → distill into a fine-tune-ready dataset →
> export tuned artifacts → re-evaluate → feed learnings back.

The repo is **general now**; concrete domains/experiments are added later as
**projects**, and **roles** (prompt-category playbooks) guide both *how to
generate a great prompt* for a category and *how to measure/improve it*.

### Goals
- **Generate** production-ready prompts from a brief (idea + workflow + role),
  optionally grounded in a repo's conventions.
- Author, version, and diff prompts as plain files (git is the history).
- Evaluate prompt/model combinations over datasets with deterministic scorers
  and an LLM-as-judge.
- Automatically optimize prompts (custom loop first; DSPy adapter later).
- Distill the best prompt into a validated, fine-tune-ready JSONL dataset.
- Export tuned behavior into artifacts usable **today**: a Claude Code skill,
  Cursor rules, and a ChatGPT custom-instructions / Custom-GPT spec.
- Track everything locally (JSONL + SQLite + Markdown reports), including
  **cost/credit spend**.

### Non-goals (for the first build)
- Hosted weight fine-tuning (deferred until an OpenAI API key is available).
- A "manual runner" routing prompts to ChatGPT/Cursor (deferred; interface
  stays open).
- Hosted observability (Langfuse / W&B) — local-first only; optional later.

---

## 2. Tools & constraints (what we build around)

| Tool | Role in the repo |
|---|---|
| **Claude Code** | The **engine**. Runs key-free via the **Claude Agent SDK** (Python `claude-agent-sdk`), reusing existing Claude Code auth. Subprocess `claude -p` is the documented fallback. Also performs **repo analysis** for repo-aware generation. |
| **Cursor** | Editing prompts/datasets; an **export target** (Cursor rules). |
| **ChatGPT website** | An **export target** (custom instructions / Custom GPT). Not an automated runner in this build. |
| **Python 3.13** | Orchestration language for the harness/CLI. |

### Engine facts (verified, current as of 2026-06)
The `claude` runner relies on Claude Code headless capabilities:
- `claude -p "<prompt>" --output-format json` → JSON with `result`,
  `usage`, **`total_cost_usd`**, `modelUsage`, `session_id`, `stop_reason`.
- `--json-schema <schema>` (with `--output-format json`) → enforced
  **structured output** in a `structured_output` field → used by the LLM-judge
  and by structured generation/critique.
- `--model opus|sonnet|haiku|fable|<full-id>` → model selection.
- `--system-prompt` / `--append-system-prompt` (+ `-file` variants).
- `--tools ""` → **pure text-in/text-out** generation (no agentic tool use) —
  the mode used for evaluation and prompt generation. (Repo analysis instead
  runs *with* read tools enabled so Claude can inspect files.)
- `--max-budget-usd <n>` → hard budget cap per invocation.
- `--bare` → skip config auto-discovery for reproducible runs.
- Multi-turn via `--resume <session-id>` / `--session-id` / `--fork-session`.
- Official **Claude Agent SDK** (`pip install claude-agent-sdk`, Python 3.10+):
  native message objects + structured output; preferred over subprocess.

### ⚠️ Credit-budget constraint (shapes the whole design)
On subscription plans, headless `-p` / Agent SDK usage draws from a **separate
monthly Agent-SDK credit pool**. Automated batch eval/optimize and deep repo
analysis therefore have a real ceiling. The design mitigates this by:
1. **Caching** model outputs by `(prompt_hash, model, example_id)` so re-scoring
   and re-runs are free.
2. **Small default eval sets** (dev split kept intentionally small).
3. **Budget caps** surfaced on every batch command (`--budget-usd`, passed to
   `--max-budget-usd`).
4. **Repo-analysis toggle** — light analysis by default; `--deep` opt-in;
   `--no-analyze` for target-only generation.
5. Recording `total_cost_usd` per run in the local ledger for visibility.

---

## 3. Core concepts (domain model)

| Concept | Definition |
|---|---|
| **Brief** | The generation input: `{ idea, role, workflow_notes, audience, inputs, constraints, output_shape, target, repo? }`. |
| **Generator** | Turns a Brief (+ role scaffold + optional repo analysis) into a Prompt via a meta-prompt ("a prompt that writes prompts"). |
| **Runner** | A key-free backend that turns messages → a response. `claude` (primary). `openai`/`manual` are future drop-ins behind the same interface. |
| **Prompt** | A versioned template (system/user with `{variables}`), stored as files; identified by name + version + content hash. |
| **Library** | Flat store of lightweight, generated prompts (versioned files) — frictionless home for one-offs. |
| **Dataset / Example** | JSONL examples with `input` (variables), optional `reference`, and `metadata`; organized into `train`/`dev`/`test` splits. |
| **Scorer** | `score(example, output) → ScoreResult{value, passed, detail}`. Deterministic or LLM-judge. |
| **Run** | A recorded execution (generate / eval / optimize / distill / export) with metrics, cost, and artifacts on disk. |
| **Optimizer** | `optimize(prompt, dataset, scorers, budget) → best prompt version + history`. Pluggable. |
| **Distiller** | Uses a strong teacher model to turn (best prompt + dataset) into fine-tune-ready data. |
| **Exporter** | Turns a prompt + exemplars into a portable artifact (Claude Code skill / Cursor rules / ChatGPT GPT). Used by both Generate and Improve. |
| **Role / TaskProfile** | A **prompt-category playbook**: a generation scaffold (structure + best-practice checklist + repo-analysis default + target default) **and** an eval scaffold (default scorers, dataset expectations, judge hints), plus an ordered improvement path. |
| **Project** | The rigorous unit of work: one domain/task with its own prompts, datasets, runs, and `project.yaml`. A library prompt is **promoted** into a project when you want to eval/optimize it. |
| **Store** | Local ledger (SQLite index + JSON artifacts + Markdown reports). |

---

## 4. Repo layout

```
prompt-vishwakarma/
├── pyproject.toml             # package, deps, `pv` CLI entry point
├── .env.example               # optional future keys (OPENAI_API_KEY, ...)
├── .gitignore  README.md
├── src/pv/
│   ├── cli.py                 # `pv` (typer + rich)
│   ├── config.py              # settings, paths, env, model/cost tables
│   ├── runners/
│   │   ├── base.py            # Runner protocol; Message/GenParams/Response/Usage
│   │   ├── claude_runner.py   # Agent SDK primary; `claude -p` subprocess fallback
│   │   ├── registry.py        # get_runner("claude"); future: "openai","manual"
│   │   └── cache.py           # output cache keyed by (prompt_hash, model, example_id)
│   ├── generate/
│   │   ├── base.py            # Brief model; Generator protocol
│   │   ├── meta_prompt.py     # the prompt-that-writes-prompts (role-parameterized)
│   │   ├── repo_analysis.py   # Claude repo scan → conventions/reusable/risks summary
│   │   └── critique.py        # single-shot critique → revised version
│   ├── prompts/
│   │   ├── model.py           # Prompt, PromptVersion, render(), content_hash
│   │   └── registry.py        # load / list / diff / new-version on disk
│   ├── datasets/
│   │   ├── model.py           # Example, Dataset, splits
│   │   └── io.py              # JSONL load + validation
│   ├── eval/
│   │   ├── harness.py         # run prompt×model over a split → Run (resumable, cached)
│   │   ├── scorers/           # exact_match, regex, contains, json_schema_valid,
│   │   │                      #   numeric_tolerance, llm_judge
│   │   └── report.py          # Markdown report + run comparison
│   ├── optimize/
│   │   ├── base.py            # Optimizer protocol
│   │   ├── llm_judge.py       # custom propose→eval→select loop (default)
│   │   └── dspy_adapter.py    # later (optional `dspy` extra)
│   ├── distill/
│   │   ├── base.py            # Distiller protocol
│   │   └── teacher.py         # Claude teacher → chat-format JSONL (+ optional pairs)
│   ├── export/
│   │   ├── base.py            # Exporter protocol
│   │   ├── claude_skill.py    # → a Claude Code skill folder
│   │   ├── cursor_rules.py    # → Cursor project rules
│   │   └── chatgpt_gpt.py     # → ChatGPT custom-instructions / Custom-GPT spec
│   ├── roles/
│   │   ├── model.py           # Role / TaskProfile (generation + eval scaffolds)
│   │   └── builtin/           # meeting.yaml, feature_design.yaml, code_review.yaml,
│   │                          #   general.yaml, writer.yaml, extract.yaml
│   └── store/
│       ├── runs.py            # SQLite index over run artifacts
│       └── paths.py
├── .claude/
│   └── commands/              # /new, /eval, /optimize, /critique, /export
├── library/                   # lightweight generated prompts
│   └── <name>/  v1.yaml · v2.yaml · brief.yaml (idea/role/provenance)
├── projects/                  # promoted, rigorous work
│   └── <domain>/  project.yaml · prompts/ · datasets/ · runs/ · README.md
├── examples/                  # one worked end-to-end project (demo + smoke test)
├── tests/
└── docs/
    └── superpowers/specs/     # this spec
```

---

## 5. Module designs

### 5.1 `runners/` — key-free engines behind one interface

```python
# base.py
class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class GenParams(BaseModel):
    model: str = "opus"          # alias or full id
    max_tokens: int = 4096
    system: str | None = None
    json_schema: dict | None = None   # when set → structured output
    budget_usd: float | None = None
    tools: list[str] | None = None    # None/[] → pure mode; ["Read","Glob",...] for repo analysis

class Usage(BaseModel):
    input_tokens: int
    output_tokens: int
    cost_usd: float

class Response(BaseModel):
    text: str
    structured: dict | None
    usage: Usage
    latency_ms: int
    model: str
    raw: dict

class Runner(Protocol):
    def complete(self, messages: list[Message], params: GenParams) -> Response: ...
```

- **`claude_runner.py`** — primary. Uses the Claude Agent SDK (`query` /
  `ClaudeAgentOptions`); **tools disabled** for pure generation/eval, **read
  tools enabled** for repo analysis. Falls back to `claude -p --output-format
  json [--tools ""] [--json-schema ...] [--model ...] [--append-system-prompt
  ...] [--max-budget-usd ...]`. Parses `result` / `structured_output` / `usage`
  / `total_cost_usd`. Exact SDK binding pinned during implementation against the
  installed `claude-agent-sdk` version.
- **`cache.py`** — content-addressed cache of `Response` keyed by
  `(prompt_content_hash, model, example_id, json_schema_hash)`. Default on;
  bypass with `--no-cache`.
- **`registry.py`** — `get_runner("claude")`. Future runners (`openai`,
  `manual`) register here without touching callers.

### 5.2 `generate/` — brief → prompt (the front door)

```python
# base.py
class Brief(BaseModel):
    idea: str                       # core task ("agenda for my MBR meeting")
    role: str                       # prompt-category playbook
    workflow_notes: str | None = None   # how it should operate
    audience: str | None = None
    inputs: list[str] = []          # what the final prompt will be given at use-time
    constraints: list[str] = []
    output_shape: str | None = None
    target: Literal["claude","cursor","chatgpt","raw"] = "raw"
    repo: Path | None = None
    analyze: Literal["light","deep","off"] = "light"

class Generator(Protocol):
    def generate(self, brief: Brief) -> tuple[PromptVersion, str]: ...  # (prompt, rationale)
```

- **`meta_prompt.py`** — the prompt-that-writes-prompts. Assembles: role
  scaffold (required sections + best-practice checklist), the Brief, an optional
  repo-analysis summary, and the target format, then runs the `claude` runner
  (pure mode, optionally structured) to emit a complete prompt: role/context,
  instructions, steps, constraints, output format, and `{variables}`.
- **`repo_analysis.py`** — **toggle** per the design:
  - `light` (default): quick scan (manifest, top-level structure, dominant
    conventions) → short summary.
  - `deep` (`--deep`): thorough pass (key dirs, component/util/test patterns,
    risks) → richer summary. Higher credit cost.
  - `off` (`--no-analyze`): skip; the generated prompt instructs the *downstream*
    agent to inspect the repo at use-time (repo-targeting only).
  Runs the `claude` runner with read tools enabled; returns a structured summary
  cached per repo+commit.
- **`critique.py`** — `pv prompt critique <name>`: Claude critiques the current
  version against the role's checklist and proposes a revised version (saved as
  the next version). Single-shot, no dataset — the lightweight refine step
  between Generate and full Optimize.

### 5.3 `prompts/` — versioned templates as files
- On disk: `library/<name>/v1.yaml` (and `projects/<p>/prompts/<name>/v1.yaml`).
  ```yaml
  description: "Build a time-boxed MBR agenda from monthly inputs."
  role: meeting
  defaults: { model: opus, max_tokens: 1024 }
  system: |
    You are an experienced monthly-business-review facilitator.
  user: |
    Inputs: {metrics}, {priorities}, {attendees}
    Produce a time-boxed agenda: wins → misses → metric deep-dives →
    decisions needed → action items.
  ```
- `model.py`: `render(variables)` with **strict** missing/extra-variable checks;
  `content_hash` over `system+user+defaults`.
- `registry.py`: `load`, `list`, `diff(vA, vB)`, `new_version(...)`. `latest`
  resolves to the highest version. Works over both `library/` and `projects/`.

### 5.4 `datasets/` — JSONL, validated
- `Example{ id, input: dict, reference: Any | None, metadata: dict }`.
- `Dataset` = named collection with `train`/`dev`/`test` JSONL files.
- `io.py`: load + validate (schema, duplicate ids, role-required fields). The
  same dataset feeds both **eval** and **distillation**.

### 5.5 `eval/` — the measurement core
- **`harness.py`**: inputs = (prompt version, runner+model, split, scorers,
  budget). For each example: render → `runner.complete` (cached) → score → write
  a **Run**. Resumable; concurrency-limited; aborts on budget cap.
- **`scorers/`**: each `score(example, output) → ScoreResult{value, passed,
  detail}`.
  - Deterministic: `exact_match`, `regex`, `contains`, `json_schema_valid`,
    `numeric_tolerance`.
  - `llm_judge`: Claude-as-judge with a rubric; returns `{score, rationale}` via
    **structured output**. Judge model configurable; default `claude-opus-4-8`;
    note `claude-haiku-4-5` for high-volume/cheap judging.
- **`report.py`**: Markdown report (aggregate metrics, per-example table,
  failures, total cost) + `compare(run_a, run_b)` (quality × cost × latency).

### 5.6 `optimize/` — pluggable, custom-first
- **`base.py`**: `optimize(prompt, dataset_dev, scorers, budget) →
  OptimizeResult{ best_version, history }`.
- **`llm_judge.py`** (default): loop — propose N variants (from best + recent
  failures) → eval each on dev (cached) → keep top → repeat until budget
  (iterations or USD) or plateau. Winner saved as a new prompt version.
- **`dspy_adapter.py`** (later): wraps DSPy MIPRO/Bootstrap behind the same
  protocol (optional `dspy` extra) → drop-in.

### 5.7 `distill/` — fine-tune-ready data from the best prompt
- **`teacher.py`**: run the best prompt through a strong teacher
  (`claude-opus-4-8` default) over the dataset → high-quality `{input → output}`
  pairs in **OpenAI chat-format JSONL**; optionally **preference pairs** (sample
  + judge) for future DPO. Validates format + token counts. Output:
  `projects/<p>/datasets/finetune/*.jsonl`, ready to train when a key exists.

### 5.8 `export/` — tuned artifacts usable today (shared by Generate + Improve)
From a prompt version (generated or optimized) + optional exemplars:
- **`claude_skill.py`** → a Claude Code skill folder (`SKILL.md` + assets).
- **`cursor_rules.py`** → a Cursor project rules file.
- **`chatgpt_gpt.py`** → a ChatGPT custom-instructions / Custom-GPT spec.
- Each: `export(prompt_version, exemplars, out_dir) → path`.

### 5.9 `roles/` — prompt-category playbooks
A `Role` (YAML) carries:
- **generation:** required prompt sections, best-practice checklist,
  `repo_analysis` default (`off`/`light`/`deep`), default `target`.
- **eval:** default scorers, dataset expectations (fields, min sizes), judge hints.
- **playbook:** ordered path — *generate → critique → (collect examples) → eval
  → optimize → export artifacts → distill dataset → [later, with API key]
  fine-tune → re-eval.*

Built-ins shipping first: **`meeting`** (agendas/plans/structured docs),
**`feature-design`** (repo-aware feature design maximizing reuse),
**`code-review`** (repo-aware, legacy-aware, structured findings), **`general`**
(catch-all), **`writer`**, **`extract`** (extraction/classification). Authors can
add custom roles as YAML. `pv role show <role>` prints the playbook;
`pv new ... --role <role>` uses its generation scaffold.

### 5.10 `store/` — local run ledger
SQLite (`runs.db`) indexing every run (generate/eval/optimize/distill/export):
type, project-or-library, prompt hash, model, metric summary, **cost_usd**,
timestamp, path to the full JSON artifact. Powers `pv runs list/show/compare`.

### 5.11 `config.py`
Settings + paths; `.env` loading (optional future keys); model alias and
**cost tables** (cross-checked against the runner's reported `total_cost_usd`).

### 5.12 CLI + Claude Code commands

`pv` (typer + rich):

| Command | Does |
|---|---|
| `pv new "<idea>" --role <r> [--repo <p>] [--deep\|--no-analyze] [--target ...]` | **generate** a prompt from a brief into `library/` |
| `pv prompt critique <name>` | single-shot critique → new version |
| `pv prompt list/diff/show` | manage prompt versions (library or project) |
| `pv export <name> --target skill\|cursor\|chatgpt` | emit a tuned artifact |
| `pv promote <name> --to-project <proj> [--role <r>]` | graduate a library prompt into a project |
| `pv init <proj> --role <r>` | scaffold a full project |
| `pv data validate/stats` | check & summarize datasets |
| `pv eval --project <p> [--prompt vN] [--model ...] [--split dev] [--budget-usd X]` | run the harness → report |
| `pv optimize --project <p> [--engine llm_judge\|dspy] [--budget ...]` | auto-improve the prompt |
| `pv distill --project <p> [--teacher ...]` | generate fine-tune data from best prompt |
| `pv runs list/show/compare` | inspect the local run ledger |
| `pv role show <role>` | print a role's playbook |

Claude Code-native wrappers in `.claude/commands/`: `/new`, `/critique`,
`/eval`, `/optimize`, `/export` — drive the same flows conversationally.

---

## 6. The workflow (end-to-end)

### Fast path (Generate) — the common case
1. `pv new "<idea>" --role <role> [--repo <path>] [--deep|--no-analyze]
   [--target claude|cursor|chatgpt]`
2. (interactive) fill the brief: audience, inputs, constraints, output shape.
3. If a repo is given and analysis is on: Claude scans it → conventions summary.
4. Meta-prompt + role scaffold + brief (+ repo summary) → **prompt v1** in
   `library/`, plus a rendered, ready-to-paste copy.
5. *(optional)* `pv prompt critique` → v2. *(optional)* `pv export` → artifact.
6. Use it.

**Worked examples:**
- *MBR agenda* — `pv new "agenda for my monthly business review" --role meeting`
  → reusable, parameterized agenda prompt; `--target chatgpt` to use in ChatGPT.
- *Next.js feature design* — `pv new "design a feature reusing existing code"
  --role feature-design --repo ~/code/myapp --target cursor` → repo-aware prompt
  exported as a Cursor rule, reused per feature.
- *Legacy review* — `pv new "review changes in our legacy repo" --role
  code-review --repo ~/code/legacy --target claude` → legacy-aware, structured
  review prompt exported as a Claude Code skill, run on any diff.

### Rigorous path (Improve) — when it's worth it
1. `pv promote <name> --to-project <proj>` (or `pv init`).
2. Build a small dataset (JSONL) of examples.
3. `pv eval` → measure across models with scorers + LLM-judge → report.
4. `pv optimize` → auto-improve → better version.
5. `pv distill` → fine-tune-ready JSONL (held for later training).
6. `pv export` → tuned artifacts (skill / Cursor / ChatGPT).
7. *(later, with an API key)* train on the distilled dataset; eval tuned vs base.
8. Feed learnings back into the prompt, dataset, and role playbook.

---

## 7. Key data formats

- **Prompt version** — YAML (see 5.3).
- **Brief** — `library/<name>/brief.yaml` (idea, role, notes, target, repo,
  analyze, provenance).
- **Dataset** — JSONL, one `Example` per line:
  ```json
  {"id": "ex-001", "input": {"diff": "..."}, "reference": null, "metadata": {}}
  ```
- **`project.yaml`**:
  ```yaml
  name: legacy-review
  role: code-review
  runner: claude
  models: { primary: opus, judge: opus }
  datasets: { train: datasets/train.jsonl, dev: datasets/dev.jsonl, test: datasets/test.jsonl }
  scorers: [json_schema_valid, llm_judge]
  optimize: { engine: llm_judge, budget_usd: 2.0 }
  distill: { teacher: opus, format: chat }   # target: openai (deferred)
  ```
- **Run record** — JSON under `…/runs/<run-id>/` + a sibling Markdown report.
- **Role** — YAML (generation + eval + playbook; see 5.9).

---

## 8. Local-first storage & cost tracking
- Briefs, prompts (library + project), datasets, project configs, run records,
  reports, exported artifacts: all in-repo, git-friendly.
- The cache and `runs.db` live under a top-level `.pv/` (and/or per project);
  `.gitignore` excludes the cache and large/regenerable run blobs by default
  (reports + run index kept).
- Every model-touching command prints and stores `cost_usd`; `pv runs list`
  shows cumulative spend so the monthly Agent-SDK credit pool stays visible.

---

## 9. Future / deferred (interfaces stay open)
- **`runners/openai_runner.py`** — inference via OpenAI API once a key exists.
- **`finetune/openai_ft.py`** — real hosted SFT/DPO training on the distilled
  dataset; register tuned model ids so `pv eval` can target them.
- **`runners/manual_runner.py`** — human-in-the-loop ChatGPT/Cursor runner.
- **`optimize/dspy_adapter.py`** — DSPy optimizers.
- **Anthropic fine-tune via Bedrock** — documented stub (select models only).
- **Hosted observability** — optional Langfuse/W&B adapters.

---

## 10. Build roadmap (each phase independently usable)
> Status: Phases 1–3 ✅ built (Generate front door + Improve path). Phases 4–6 pending.

1. **Foundations** — package skeleton, `config`, `runners/claude` (Agent SDK +
   subprocess fallback) + cache, prompts model/registry, `library/` storage.
   *Outcome: call Claude key-free with versioned prompts.*
2. **Generate (the front door)** — `generate/` (meta-prompt, repo-analysis
   toggle, critique), the first **roles** as generation playbooks, `export/`
   (skill / Cursor / ChatGPT), `pv new` / `pv prompt critique` / `pv export`,
   `.claude/commands/{new,critique,export}`. *Outcome: brief → ready-to-use,
   exportable prompt — your three examples work end-to-end.*
3. **Eval** — harness + deterministic scorers + LLM-judge + reports + run store +
   `pv promote`/`pv init`. *Outcome: measure prompt quality, see cost.*
4. **Optimize** — custom LLM-judge loop. *Outcome: auto-improve prompts.*
5. **Distill** — teacher → fine-tune-ready dataset. *Outcome: asset ready for
   real training later.*
6. **Later/optional** — OpenAI runner + real fine-tuning, manual runner, DSPy,
   Bedrock, hosted observability, richer roles.

---

## 11. Risks & open questions
- **Agent-SDK credit budget** is the main operational risk → mitigated by cache,
  small N, budget caps, repo-analysis toggle, cost visibility.
- **Exact `claude-agent-sdk` binding** (structured output, tool enable/disable)
  pinned to the installed version at implementation time; `claude -p` fallback.
- **Repo analysis quality/cost** — `light` default keeps cost low; `--deep` for
  when tailoring matters; cached per repo+commit.
- **Determinism** — Claude 4.x exposes no `temperature`; eval relies on
  scorers/judges rather than exact reproduction.
- **OpenAI model/SDK specifics** for the deferred fine-tune path confirmed when
  that phase starts (and a key is available).

---

## 12. Decisions on record
- **Primary use = Generate:** brief (idea + workflow + role, optional repo) →
  ready-to-use prompt is the front door; Improve (eval/optimize/distill) is the
  opt-in rigorous path.
- **Engine:** Claude Code, key-free, via the **Claude Agent SDK** (subprocess
  fallback) — no API key needed to start.
- **Repo-aware generation:** **toggle** — `light` default, `--deep`, `--no-analyze`.
- **Storage:** generated prompts land in a lightweight **`library/`**; **`promote`**
  into a `project/` for rigorous work.
- **Scope:** general framework now; domains added later as projects; **roles are
  prompt-category playbooks** (generation + eval).
- **Roles shipping first:** `meeting`, `feature-design`, `code-review`,
  `general`, `writer`, `extract`.
- **Tracking:** local-first (JSONL + SQLite + Markdown).
- **Optimizer:** pluggable — custom LLM-judge loop first, DSPy adapter later.
- **Fine-tune (given no API):** produce **both** portable tuned **artifacts**
  (Claude Code skill / Cursor rules / ChatGPT GPT) **and** a fine-tune-ready
  **dataset** for real training later.
- **ChatGPT/Cursor:** export targets now; no manual runner yet. OpenAI API runner
  + hosted fine-tuning are deferred drop-ins behind open interfaces.
