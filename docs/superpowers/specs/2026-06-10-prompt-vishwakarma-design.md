# Prompt Vishwakarma — Design Spec

- **Date:** 2026-06-10
- **Repo:** `prompt-vishwakarma` (https://github.com/Nittuz/prompt-vishwakarma.git)
- **Package / CLI:** `pv`
- **Status:** Approved design — ready for implementation planning

---

## 1. Purpose

A **local-first toolkit for improving prompts and producing "fine-tunes"** using
only the tools the author already has — **Claude Code**, **Cursor**, and the
**ChatGPT website** — with **no API key required to start**.

It supports the full flywheel:

> author + version a prompt → evaluate it → automatically optimize it →
> distill the best prompt into a fine-tune-ready dataset → export the tuned
> behavior into usable artifacts → re-evaluate → feed learnings back.

The repo is **general now**; concrete domains are added later as **projects**, and
**roles** (task-profile playbooks) guide the author from the general toolkit
toward a better outcome for a given kind of task.

### Goals
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
| **Claude Code** | The **engine**. Runs key-free via the **Claude Agent SDK** (Python `claude-agent-sdk`), reusing existing Claude Code auth. Subprocess `claude -p` is the documented fallback. |
| **Cursor** | Editing prompts/datasets; an **export target** (Cursor rules). |
| **ChatGPT website** | An **export target** (custom instructions / Custom GPT). Not an automated runner in this build. |
| **Python 3.13** | Orchestration language for the harness/CLI. |

### Engine facts (verified, current as of 2026-06)
The `claude` runner relies on Claude Code headless capabilities:
- `claude -p "<prompt>" --output-format json` → JSON with `result`,
  `usage`, **`total_cost_usd`**, `modelUsage`, `session_id`, `stop_reason`.
- `--json-schema <schema>` (with `--output-format json`) → enforced
  **structured output** in a `structured_output` field → used by the LLM-judge.
- `--model opus|sonnet|haiku|fable|<full-id>` → model selection.
- `--system-prompt` / `--append-system-prompt` (+ `-file` variants).
- `--tools ""` → **pure text-in/text-out** generation (no agentic tool use) —
  the mode used for evaluation.
- `--max-budget-usd <n>` → hard budget cap per invocation.
- `--bare` → skip config auto-discovery for reproducible runs.
- Multi-turn via `--resume <session-id>` / `--session-id` / `--fork-session`.
- Official **Claude Agent SDK** (`pip install claude-agent-sdk`, Python 3.10+):
  native message objects + structured output; preferred over subprocess.

### ⚠️ Credit-budget constraint (shapes the whole design)
On subscription plans, headless `-p` / Agent SDK usage draws from a **separate
monthly Agent-SDK credit pool**. Automated batch eval/optimize therefore has a
real ceiling. The design mitigates this by:
1. **Caching** model outputs by `(prompt_hash, model, example_id)` so re-scoring
   and re-runs are free.
2. **Small default eval sets** (dev split kept intentionally small).
3. **Budget caps** surfaced on every batch command (`--budget-usd`, passed to
   `--max-budget-usd`).
4. Recording `total_cost_usd` per run in the local ledger for visibility.

---

## 3. Core concepts (domain model)

| Concept | Definition |
|---|---|
| **Runner** | A key-free backend that turns messages → a response. `claude` (primary). `openai`/`manual` are future drop-ins behind the same interface. |
| **Prompt** | A versioned template (system/user with `{variables}`), stored as files; identified by name + version + content hash. |
| **Dataset / Example** | JSONL examples with `input` (variables), optional `reference`, and `metadata`; organized into `train`/`dev`/`test` splits. |
| **Scorer** | `score(example, output) → ScoreResult{value, passed, detail}`. Deterministic or LLM-judge. |
| **Run** | A recorded execution (eval / optimize / distill / export) with metrics, cost, and artifacts on disk. |
| **Optimizer** | `optimize(prompt, dataset, scorers, budget) → best prompt version + history`. Pluggable. |
| **Distiller** | Uses a strong teacher model to turn (best prompt + dataset) into fine-tune-ready data. |
| **Exporter** | Turns the winning prompt + exemplars into a portable artifact (Claude Code skill / Cursor rules / ChatGPT GPT). |
| **Role / TaskProfile** | A named playbook bundling recommended models, a prompt scaffold, default scorers, dataset expectations, and an ordered improvement path. |
| **Project** | The unit of work: one domain/task with its own prompts, datasets, runs, and `project.yaml`. |
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
│   │   ├── model.py           # Role / TaskProfile
│   │   └── builtin/           # classifier.yaml, extractor.yaml, summarizer.yaml,
│   │                          #   assistant.yaml, coder.yaml
│   └── store/
│       ├── runs.py            # SQLite index over run artifacts
│       └── paths.py
├── .claude/
│   └── commands/              # /eval, /optimize, /curate, /export (Claude Code-native)
├── projects/
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
  `ClaudeAgentOptions`) with **tools disabled** for pure generation; falls back
  to `claude -p --output-format json --tools "" [--json-schema ...] [--model ...]
  [--append-system-prompt ...] [--max-budget-usd ...]`. Parses `result` /
  `structured_output` / `usage` / `total_cost_usd`. Exact SDK binding pinned
  during implementation against the installed `claude-agent-sdk` version.
- **`cache.py`** — content-addressed cache of `Response` keyed by
  `(prompt_content_hash, model, example_id, json_schema_hash)`. Default on;
  bypass with `--no-cache`.
- **`registry.py`** — `get_runner("claude")`. Future runners (`openai`,
  `manual`) register here without touching callers.

### 5.2 `prompts/` — versioned templates as files
- On disk: `projects/<p>/prompts/<name>/v1.yaml`, `v2.yaml`, …
  ```yaml
  description: "Classify a support message into an intent label."
  defaults: { model: opus, max_tokens: 256 }
  system: |
    You are an intent classifier. Reply with exactly one label.
  user: |
    Message: {message}
    Labels: {labels}
  ```
- `model.py`: `render(variables)` with **strict** missing/extra-variable checks;
  `content_hash` over `system+user+defaults`.
- `registry.py`: `load`, `list`, `diff(vA, vB)`, `new_version(...)`. `latest`
  resolves to the highest version.

### 5.3 `datasets/` — JSONL, validated
- `Example{ id, input: dict, reference: Any | None, metadata: dict }`.
- `Dataset` = named collection with `train`/`dev`/`test` JSONL files.
- `io.py`: load + validate (schema, duplicate ids, role-required fields). The
  same dataset feeds both **eval** and **distillation**.

### 5.4 `eval/` — the measurement core
- **`harness.py`**: inputs = (prompt version, runner+model, split, scorers,
  budget). For each example: render → `runner.complete` (cached) → score → write
  a **Run**. Resumable; concurrency-limited; aborts on budget cap.
- **`scorers/`**: each `score(example, output) → ScoreResult{value: float,
  passed: bool, detail: str}`.
  - Deterministic: `exact_match`, `regex`, `contains`, `json_schema_valid`,
    `numeric_tolerance`.
  - `llm_judge`: Claude-as-judge with a rubric; returns `{score, rationale}` via
    **structured output** (`--json-schema`). Judge model configurable; default
    `claude-opus-4-8`; note `claude-haiku-4-5` for high-volume/cheap judging.
- **`report.py`**: Markdown report (aggregate metrics, per-example table,
  failures, total cost) + `compare(run_a, run_b)` for prompt-vs-prompt or
  model-vs-model (quality × cost × latency).

### 5.5 `optimize/` — pluggable, custom-first
- **`base.py`**: `optimize(prompt, dataset_dev, scorers, budget) →
  OptimizeResult{ best_version, history }`.
- **`llm_judge.py`** (default): loop —
  1. Claude proposes N prompt variants from current best + recent failure cases.
  2. Harness evals each variant on the dev split (cached).
  3. Keep top performer(s).
  4. Repeat until budget (iterations or USD) or plateau.
  Each iteration is a logged run; the winner is saved as a **new prompt version**.
- **`dspy_adapter.py`** (later): wraps DSPy MIPRO/Bootstrap behind the same
  protocol (optional `dspy` extra). Same in/out contract → drop-in.

### 5.6 `distill/` — fine-tune-ready data from the best prompt
- **`teacher.py`**: run the **best prompt** through a strong teacher
  (`claude-opus-4-8` by default) over the dataset to produce high-quality
  `{input → output}` pairs in **OpenAI chat-format JSONL**; optionally produce
  **preference pairs** (sample + judge) for future DPO. Validates format + token
  counts. Output: `projects/<p>/datasets/finetune/*.jsonl` ready to train when an
  API key exists.

### 5.7 `export/` — tuned artifacts usable today
From the winning prompt + top exemplars, generate:
- **`claude_skill.py`** → a Claude Code skill folder (`SKILL.md` + assets).
- **`cursor_rules.py`** → Cursor project rules file.
- **`chatgpt_gpt.py`** → a ChatGPT custom-instructions / Custom-GPT spec
  (Markdown the author pastes into ChatGPT).
- Each exporter: `export(prompt_version, exemplars, out_dir) → path`.

### 5.8 `roles/` — task-profile playbooks
A `Role` (YAML) bundles: recommended models (teacher/judge), a prompt scaffold,
default scorers, dataset expectations (fields, min sizes), and an ordered
**playbook**:

> prompt-first → optimize → export tuned artifacts (skill / Cursor rules / GPT)
> → distill dataset → [later, when API key exists] fine-tune → re-eval.

Built-ins: `classifier`, `extractor`, `summarizer`, `assistant`, `coder`.
`pv role show <role>` prints the playbook; `pv init <project> --role <role>`
scaffolds a project pre-wired with that role's prompt/scorers/config.

### 5.9 `store/` — local run ledger
SQLite (`runs.db`) indexing every run: type, project, prompt hash, model, metric
summary, **cost_usd**, timestamp, and a path to the full JSON artifact under
`projects/<p>/runs/`. Powers `pv runs list/show/compare` without re-reading files.

### 5.10 `config.py`
Settings + paths; `.env` loading (optional future keys); model alias and
**cost tables** (for cost estimation independent of, and cross-checked against,
the runner's reported `total_cost_usd`).

### 5.11 CLI + Claude Code commands

`pv` (typer + rich):

| Command | Does |
|---|---|
| `pv init <name> --role <role>` | scaffold a project from a role |
| `pv prompt new/list/diff` | manage prompt versions |
| `pv data validate/stats` | check & summarize datasets |
| `pv eval --project <p> [--prompt vN] [--model ...] [--split dev] [--budget-usd X]` | run the harness → report |
| `pv optimize --project <p> [--engine llm_judge\|dspy] [--budget ...]` | auto-improve the prompt |
| `pv distill --project <p> [--teacher ...]` | generate fine-tune data from best prompt |
| `pv export --project <p> --target skill\|cursor\|chatgpt` | emit a tuned artifact |
| `pv runs list/show/compare` | inspect the local run ledger |
| `pv role show <role>` | print a role's playbook |

Claude Code-native wrappers in `.claude/commands/`: `/eval`, `/optimize`,
`/curate`, `/export` — drive the same harness conversationally from inside
Claude Code.

---

## 6. The flywheel (end-to-end)

1. `pv init support-intent --role classifier` → scaffolds a project.
2. Author/curate the prompt (`prompts/intent/v1.yaml`) and datasets (JSONL).
3. `pv eval` → measure v1 across models with scorers + LLM-judge → report.
4. `pv optimize` → custom loop proposes/evaluates variants → saves a better
   version (v2…).
5. `pv distill` → Claude teacher turns best prompt + dataset into fine-tune-ready
   JSONL (held for later training).
6. `pv export --target skill|cursor|chatgpt` → tuned artifacts usable **now** in
   Claude Code / Cursor / ChatGPT.
7. (Later, with an API key) train on the distilled dataset; `pv eval` the tuned
   model vs base vs prompted-strong.
8. Feed learnings back into the prompt, dataset, and role playbook.

---

## 7. Key data formats

- **Prompt version** — YAML (see 5.2).
- **Dataset** — JSONL, one `Example` per line:
  ```json
  {"id": "ex-001", "input": {"message": "where is my order", "labels": "shipping|billing|other"}, "reference": "shipping", "metadata": {}}
  ```
- **`project.yaml`**:
  ```yaml
  name: support-intent
  role: classifier
  runner: claude
  models: { primary: opus, judge: opus }
  datasets: { train: datasets/train.jsonl, dev: datasets/dev.jsonl, test: datasets/test.jsonl }
  scorers: [exact_match, llm_judge]
  optimize: { engine: llm_judge, budget_usd: 2.0 }
  distill: { teacher: opus, format: chat }   # target: openai (deferred)
  ```
- **Run record** — JSON under `projects/<p>/runs/<run-id>/` (config, per-example
  outputs+scores, aggregate metrics, cost) + a sibling Markdown report.
- **Role** — YAML (see 5.8).

---

## 8. Local-first storage & cost tracking
- Datasets, prompts, project configs, run records, reports, exported artifacts:
  all in-repo, git-friendly.
- The cache and `runs.db` live under each project (or a top-level `.pv/` cache);
  `.gitignore` excludes the cache and large/regenerable run blobs by default
  (reports + run index kept).
- Every batch command prints and stores `cost_usd`; `pv runs list` shows
  cumulative spend so the monthly Agent-SDK credit pool stays visible.

---

## 9. Future / deferred (interfaces stay open)
- **`runners/openai_runner.py`** — inference via OpenAI API once a key exists.
- **`finetune/openai_ft.py`** — real hosted SFT/DPO training jobs on the
  distilled dataset; register tuned model ids so `pv eval` can target them.
- **`runners/manual_runner.py`** — human-in-the-loop ChatGPT/Cursor runner
  (copy-paste batches), for credit-free generation and second-model comparison.
- **`optimize/dspy_adapter.py`** — DSPy optimizers.
- **Anthropic fine-tune via Bedrock** — documented stub (select models only).
- **Hosted observability** — optional Langfuse/W&B adapters.

---

## 10. Build roadmap (each phase independently usable)
1. **Foundations** — package skeleton, `config`, `runners/claude` (Agent SDK +
   subprocess fallback) + cache, prompts registry, datasets. *Outcome: call
   Claude key-free with versioned prompts.*
2. **Eval** — harness + deterministic scorers + LLM-judge + reports + run store.
   *Outcome: measure prompt quality, see cost.*
3. **Optimize** — custom LLM-judge loop. *Outcome: auto-improve prompts.*
4. **Distill + Export** — teacher → fine-tune-ready dataset; skill / Cursor /
   ChatGPT exporters. *Outcome: tuned artifacts now + dataset for later.*
5. **Roles + polish** — built-in roles/playbooks, `pv init`, example project,
   `.claude/commands`, docs.
6. **Later/optional** — OpenAI runner + real fine-tuning, manual runner, DSPy,
   Bedrock, hosted observability.

---

## 11. Risks & open questions
- **Agent-SDK credit budget** is the main operational risk → mitigated by cache,
  small N, budget caps, cost visibility. Revisit if limits bite.
- **Exact `claude-agent-sdk` binding** (structured output, tool-disable) pinned
  to the installed version at implementation time; subprocess `claude -p` is the
  guaranteed fallback.
- **Determinism** — Claude 4.x exposes no `temperature`; eval treats outputs as
  non-deterministic and relies on scorers/judges rather than exact reproduction.
- **OpenAI model/SDK specifics** for the deferred fine-tune path are confirmed
  when that phase starts (and a key is available).

---

## 12. Decisions on record
- **Engine:** Claude Code, key-free, via **Claude Agent SDK** (subprocess
  fallback) — no API key needed to start.
- **Scope:** general framework now; **domains added later as projects**; **roles**
  provide guided playbooks.
- **Tracking:** **local-first** (JSONL + SQLite + Markdown).
- **Optimizer:** **pluggable** — custom LLM-judge loop first, DSPy adapter later.
- **Fine-tune (given no API):** produce **both** portable tuned **artifacts**
  (Claude Code skill / Cursor rules / ChatGPT GPT) **and** a fine-tune-ready
  **dataset** for real training later.
- **ChatGPT/Cursor:** **export targets** for now; **no manual runner** yet.
  OpenAI API runner + hosted fine-tuning are **deferred drop-ins** behind the
  existing interfaces (author plans to obtain an OpenAI API key later).
