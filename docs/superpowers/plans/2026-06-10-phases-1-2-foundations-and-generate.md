# Phases 1–2: Foundations + Generate Front Door — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (inline) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Deliver the `pv new` workflow end-to-end — a brief (idea + role + optional repo) generates a versioned, ready-to-use prompt via the key-free Claude engine, exportable to Claude Code / Cursor / ChatGPT.

**Architecture:** A Python package `pv` with a `Runner` abstraction over a key-free Claude engine (subprocess `claude -p` first; Agent SDK is a documented follow-up). A `Generator` runs a role-parameterized meta-prompt (optionally grounded by repo analysis) to emit a `PromptVersion` into a lightweight `library/`. Exporters turn a prompt into portable artifacts. A `typer` CLI ties it together. All model calls go through the `Runner`, so tests inject a `FakeRunner` and never spend credits.

**Tech Stack:** Python 3.13, pydantic v2, typer, rich, pyyaml, python-dotenv; pytest for tests. Engine: `claude -p --output-format json` subprocess.

**Scope note:** This plan covers spec Phases 1–2 only. Eval / optimize / distill (Phases 3–5) and the Agent SDK runner / OpenAI runner are separate follow-up plans; their interfaces are stubbed but not implemented here.

**Implementation decisions (deviations from spec, recorded):**
- **Engine v1 = subprocess `claude -p`** (the spec's documented fallback), not the Agent SDK. Reason: dependency-free, synchronous, trivially testable; the Agent SDK adapter is a Phase-6 follow-up behind the same `Runner` protocol. Documented in README.
- `pv promote` / `pv init` / `pv eval` / `pv optimize` / `pv distill` are **registered as CLI stubs** that print "coming in Phase N" so the surface is discoverable but honest.

---

## File structure

```
pyproject.toml                     # package + deps + `pv` entry point
README.md  .env.example  .gitignore
src/pv/
  __init__.py                      # __version__
  config.py                        # paths, settings, model aliases, cost table
  runners/
    __init__.py
    base.py                        # Message, GenParams, Usage, Response, Runner
    cache.py                       # content-addressed response cache
    claude_runner.py               # subprocess `claude -p` implementation
    fake_runner.py                 # deterministic runner for tests/CLI smoke
    registry.py                    # get_runner(name)
  prompts/
    __init__.py
    model.py                       # PromptVersion (render, content_hash)
    registry.py                    # PromptStore over library/ and projects/
  generate/
    __init__.py
    base.py                        # Brief, Generator protocol
    repo_analysis.py               # analyze(repo, depth) via runner
    meta_prompt.py                 # build meta-prompt + generate()
    critique.py                    # critique() → revised version
  roles/
    __init__.py
    model.py                       # Role model + load_role/list_roles
    builtin/
      meeting.yaml  feature_design.yaml  code_review.yaml
      general.yaml  writer.yaml  extract.yaml
  export/
    __init__.py
    base.py                        # Exporter protocol, slugify
    claude_skill.py  cursor_rules.py  chatgpt_gpt.py
  store/
    __init__.py
    paths.py                       # repo root, library, .pv cache, runs.db
    runs.py                        # minimal SQLite run ledger
  cli.py                           # typer app: new/prompt/export/role/runs + stubs
.claude/commands/ new.md  critique.md  export.md
library/.gitkeep
tests/
  test_config.py test_runner.py test_cache.py test_prompts.py
  test_brief.py test_meta_prompt.py test_roles.py test_repo_analysis.py
  test_critique.py test_export.py test_store.py test_cli.py
examples/README.md
```

---

## Task 1: Package skeleton

**Files:** Create `pyproject.toml`, `src/pv/__init__.py`, `.gitignore`, `.env.example`, `README.md`, `library/.gitkeep`, `examples/README.md`.

- [ ] **Step 1: `pyproject.toml`** — PEP 621, `name="pv"`, `requires-python=">=3.10"`, deps `pydantic>=2`, `typer>=0.12`, `rich`, `pyyaml`, `python-dotenv`; `[project.optional-dependencies] dev=["pytest"]`; `[project.scripts] pv="pv.cli:app"`; setuptools `package-dir={""="src"}`, `packages.find` under `src`.
- [ ] **Step 2: `src/pv/__init__.py`** → `__version__ = "0.1.0"`.
- [ ] **Step 3: `.gitignore`** → `__pycache__/`, `*.pyc`, `.pv/`, `*.egg-info/`, `.pytest_cache/`, `.venv/`, `dist/`, `build/`.
- [ ] **Step 4: `.env.example`** → comment that no key is needed; placeholders `# OPENAI_API_KEY=` (future).
- [ ] **Step 5: README** → quickstart (`pip install -e ".[dev]"`, `pv new "..." --role meeting`), engine note (subprocess `claude -p`, key-free), link to spec.
- [ ] **Step 6: `library/.gitkeep`, `examples/README.md`** (one-line placeholder).
- [ ] **Step 7: Install** — `python3 -m pip install -e ".[dev]"`; expect success. **Commit.**

---

## Task 2: `config.py` and `store/paths.py`

**Files:** Create `src/pv/config.py`, `src/pv/store/__init__.py`, `src/pv/store/paths.py`, `tests/test_config.py`.

- [ ] **Step 1: Failing test** `tests/test_config.py`:
```python
from pv.config import resolve_model, MODEL_ALIASES
from pv.store import paths

def test_model_alias_resolution():
    assert resolve_model("opus") == MODEL_ALIASES["opus"]
    assert resolve_model("claude-opus-4-8") == "claude-opus-4-8"  # passthrough

def test_paths_under_root(tmp_path):
    root = paths.repo_root(start=tmp_path)
    assert (paths.library_dir(root)).name == "library"
    assert paths.cache_dir(root).parts[-2:] == (".pv", "cache")
```
- [ ] **Step 2: Run** `pytest tests/test_config.py -v` → FAIL (import error).
- [ ] **Step 3: Implement `store/paths.py`**: `repo_root(start=None)` walks up for `pyproject.toml` else cwd; `library_dir(root)`, `projects_dir(root)`, `cache_dir(root)` → `root/.pv/cache`, `runs_db(root)` → `root/.pv/runs.db`. All return `pathlib.Path`, creating parents on write (helpers `ensure(p)`).
- [ ] **Step 4: Implement `config.py`**: `MODEL_ALIASES = {"opus":"claude-opus-4-8","sonnet":"claude-sonnet-4-6","haiku":"claude-haiku-4-5","fable":"claude-fable-5"}`; `resolve_model(m)` returns alias value or `m` unchanged; `COST_PER_MTOK` table (best-effort, used only as fallback when runner omits cost); `load_dotenv()` call guarded.
- [ ] **Step 5: Run** `pytest tests/test_config.py -v` → PASS. **Commit.**

---

## Task 3: Runner interface + cache

**Files:** Create `src/pv/runners/__init__.py`, `base.py`, `cache.py`, `tests/test_cache.py`.

- [ ] **Step 1: Implement `runners/base.py`** (pydantic models + Protocol):
```python
from __future__ import annotations
from typing import Protocol, Literal, Any
from pydantic import BaseModel

class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str

class GenParams(BaseModel):
    model: str = "opus"
    max_tokens: int = 4096
    system: str | None = None
    json_schema: dict | None = None
    budget_usd: float | None = None
    tools: list[str] = []          # [] → pure mode; e.g. ["Read","Glob","Grep"] for repo scan

class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

class Response(BaseModel):
    text: str
    structured: dict | None = None
    usage: Usage = Usage()
    latency_ms: int = 0
    model: str = ""
    raw: dict[str, Any] = {}

class Runner(Protocol):
    name: str
    def complete(self, messages: list[Message], params: GenParams) -> Response: ...
```
- [ ] **Step 2: Failing test** `tests/test_cache.py`:
```python
from pv.runners.cache import ResponseCache
from pv.runners.base import Response, Usage

def test_cache_roundtrip(tmp_path):
    c = ResponseCache(tmp_path)
    key = c.key(prompt="hi", model="opus", extra={"schema": None})
    assert c.get(key) is None
    r = Response(text="ok", usage=Usage(cost_usd=0.01), model="opus")
    c.put(key, r)
    got = c.get(key)
    assert got is not None and got.text == "ok" and got.usage.cost_usd == 0.01
```
- [ ] **Step 3: Run** → FAIL.
- [ ] **Step 4: Implement `runners/cache.py`**: `ResponseCache(dir)`; `key(**parts)` = sha256 of `json.dumps(parts, sort_keys=True, default=str)`; `get(key)` reads `dir/<key>.json` → `Response.model_validate_json` or None; `put(key, resp)` writes `resp.model_dump_json()`. Create dir on init.
- [ ] **Step 5: Run** `pytest tests/test_cache.py -v` → PASS. **Commit.**

---

## Task 4: Claude subprocess runner + fake runner + registry

**Files:** Create `src/pv/runners/claude_runner.py`, `fake_runner.py`, `registry.py`, `tests/test_runner.py`.

- [ ] **Step 1: Implement `runners/claude_runner.py`** — builds and runs the CLI, parses JSON. Key design: a `build_command(messages, params)` pure function (testable without invoking), and `complete()` that shells out.
```python
import json, shutil, subprocess, time
from .base import Message, GenParams, Response, Usage
from ..config import resolve_model

class ClaudeRunner:
    name = "claude"
    def __init__(self, binary: str = "claude"):
        self.binary = binary

    def build_command(self, params: GenParams) -> list[str]:
        cmd = [self.binary, "-p", "--output-format", "json", "--bare",
               "--model", resolve_model(params.model)]
        # pure text mode unless tools requested
        if params.tools:
            cmd += ["--allowedTools", ",".join(params.tools)]
        else:
            cmd += ["--tools", ""]
        if params.system:
            cmd += ["--append-system-prompt", params.system]
        if params.json_schema is not None:
            cmd += ["--json-schema", json.dumps(params.json_schema)]
        if params.budget_usd is not None:
            cmd += ["--max-budget-usd", str(params.budget_usd)]
        return cmd

    @staticmethod
    def render_stdin(messages: list[Message]) -> str:
        # system goes via --append-system-prompt; concatenate non-system turns
        return "\n\n".join(m.content for m in messages if m.role != "system")

    @staticmethod
    def parse(stdout: str) -> Response:
        data = json.loads(stdout)
        usage = data.get("usage", {}) or {}
        return Response(
            text=data.get("result", ""),
            structured=data.get("structured_output"),
            usage=Usage(
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                cost_usd=data.get("total_cost_usd", 0.0),
            ),
            model=data.get("modelUsage", {}) and next(iter(data["modelUsage"]), "") or "",
            raw=data,
        )

    def complete(self, messages, params):
        if shutil.which(self.binary) is None:
            raise RuntimeError(
                f"'{self.binary}' not found on PATH. The claude runner needs the "
                "Claude Code CLI. Set PV_RUNNER=fake for offline use."
            )
        sys_msgs = [m.content for m in messages if m.role == "system"]
        if sys_msgs and not params.system:
            params = params.model_copy(update={"system": "\n\n".join(sys_msgs)})
        cmd = self.build_command(params)
        t0 = time.time()
        proc = subprocess.run(cmd, input=self.render_stdin(messages),
                              capture_output=True, text=True)
        if proc.returncode != 0:
            raise RuntimeError(f"claude failed ({proc.returncode}): {proc.stderr[:500]}")
        resp = self.parse(proc.stdout)
        resp.latency_ms = int((time.time() - t0) * 1000)
        return resp
```
- [ ] **Step 2: Implement `runners/fake_runner.py`** — deterministic, offline:
```python
import json
from .base import Message, GenParams, Response, Usage

class FakeRunner:
    name = "fake"
    def __init__(self, responder=None):
        # responder(messages, params) -> str | dict ; default echoes
        self.responder = responder
        self.calls = []

    def complete(self, messages: list[Message], params: GenParams) -> Response:
        self.calls.append((messages, params))
        if self.responder:
            out = self.responder(messages, params)
        elif params.json_schema is not None:
            out = {"_fake": True}
        else:
            out = "FAKE: " + (messages[-1].content if messages else "")
        if isinstance(out, dict):
            return Response(text=json.dumps(out), structured=out,
                            usage=Usage(cost_usd=0.0), model=params.model)
        return Response(text=out, usage=Usage(cost_usd=0.0), model=params.model)
```
- [ ] **Step 3: Implement `runners/registry.py`**:
```python
import os
from .claude_runner import ClaudeRunner
from .fake_runner import FakeRunner

def get_runner(name: str = "claude"):
    if os.getenv("PV_RUNNER") == "fake" or name == "fake":
        return FakeRunner()
    if name == "claude":
        return ClaudeRunner()
    raise ValueError(f"unknown runner: {name}")
```
- [ ] **Step 4: Failing test** `tests/test_runner.py`:
```python
import json
from pv.runners.claude_runner import ClaudeRunner
from pv.runners.base import GenParams, Message
from pv.runners.registry import get_runner

def test_build_command_pure_mode():
    cmd = ClaudeRunner().build_command(GenParams(model="opus"))
    assert cmd[:2] == ["claude", "-p"]
    assert "--output-format" in cmd and "json" in cmd
    assert "--model" in cmd and "claude-opus-4-8" in cmd
    i = cmd.index("--tools"); assert cmd[i+1] == ""   # pure mode

def test_build_command_tools_and_schema():
    p = GenParams(model="sonnet", tools=["Read","Glob"], json_schema={"type":"object"}, system="be terse")
    cmd = ClaudeRunner().build_command(p)
    assert "--allowedTools" in cmd and "Read,Glob" in cmd
    assert "--json-schema" in cmd
    assert "--append-system-prompt" in cmd and "be terse" in cmd

def test_parse_json_output():
    out = json.dumps({"result":"hello","total_cost_usd":0.02,
                      "usage":{"input_tokens":5,"output_tokens":3},
                      "structured_output":{"k":"v"}})
    r = ClaudeRunner.parse(out)
    assert r.text == "hello" and r.usage.cost_usd == 0.02
    assert r.structured == {"k":"v"} and r.usage.input_tokens == 5

def test_registry_fake(monkeypatch):
    monkeypatch.setenv("PV_RUNNER","fake")
    r = get_runner("claude")
    assert r.name == "fake"
    resp = r.complete([Message(role="user",content="hi")], GenParams())
    assert resp.text.startswith("FAKE")
```
- [ ] **Step 5: Run** `pytest tests/test_runner.py -v` → PASS (after impl). **Commit.**

---

## Task 5: Prompt model + registry

**Files:** Create `src/pv/prompts/__init__.py`, `model.py`, `registry.py`, `tests/test_prompts.py`.

- [ ] **Step 1: Implement `prompts/model.py`**:
```python
from __future__ import annotations
import hashlib, re
from pydantic import BaseModel

_VAR = re.compile(r"{(\w+)}")

class PromptVersion(BaseModel):
    name: str
    version: int = 1
    role: str | None = None
    description: str = ""
    defaults: dict = {}
    system: str = ""
    user: str = ""

    @property
    def content_hash(self) -> str:
        blob = f"{self.system}\x00{self.user}\x00{sorted(self.defaults.items())}"
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    def variables(self) -> set[str]:
        return set(_VAR.findall(self.system)) | set(_VAR.findall(self.user))

    def render(self, variables: dict) -> tuple[str, str]:
        missing = self.variables() - set(variables)
        if missing:
            raise KeyError(f"missing variables: {sorted(missing)}")
        fmt = lambda s: s.format(**{k: variables[k] for k in self.variables()}) if self.variables() else s
        return fmt(self.system), fmt(self.user)
```
- [ ] **Step 2: Implement `prompts/registry.py`** — file-backed over `library/<name>/vN.yaml`:
```python
from __future__ import annotations
import yaml
from pathlib import Path
from .model import PromptVersion

class PromptStore:
    def __init__(self, base: Path):
        self.base = Path(base); self.base.mkdir(parents=True, exist_ok=True)

    def _dir(self, name): return self.base / name

    def versions(self, name) -> list[int]:
        d = self._dir(name)
        if not d.exists(): return []
        return sorted(int(p.stem[1:]) for p in d.glob("v*.yaml"))

    def load(self, name, version: int | None = None) -> PromptVersion:
        vs = self.versions(name)
        if not vs: raise FileNotFoundError(name)
        v = version or vs[-1]
        data = yaml.safe_load((self._dir(name) / f"v{v}.yaml").read_text())
        return PromptVersion(name=name, version=v, **data)

    def save_new_version(self, p: PromptVersion) -> PromptVersion:
        d = self._dir(p.name); d.mkdir(parents=True, exist_ok=True)
        nextv = (self.versions(p.name)[-1] + 1) if self.versions(p.name) else 1
        p = p.model_copy(update={"version": nextv})
        body = {k: getattr(p, k) for k in ("role","description","defaults","system","user")}
        (d / f"v{nextv}.yaml").write_text(yaml.safe_dump(body, sort_keys=False))
        return p

    def list(self) -> list[str]:
        return sorted(d.name for d in self.base.iterdir() if d.is_dir()) if self.base.exists() else []
```
- [ ] **Step 3: Failing test** `tests/test_prompts.py`:
```python
import pytest
from pv.prompts.model import PromptVersion
from pv.prompts.registry import PromptStore

def test_render_and_missing():
    p = PromptVersion(name="x", system="Role.", user="Hi {who}")
    assert p.render({"who":"Sam"}) == ("Role.", "Hi Sam")
    with pytest.raises(KeyError):
        p.render({})

def test_versioning(tmp_path):
    s = PromptStore(tmp_path)
    a = s.save_new_version(PromptVersion(name="agenda", system="s", user="u {x}"))
    assert a.version == 1
    b = s.save_new_version(PromptVersion(name="agenda", system="s2", user="u2 {x}"))
    assert b.version == 2 and s.versions("agenda") == [1,2]
    assert s.load("agenda").version == 2
    assert s.list() == ["agenda"]
```
- [ ] **Step 4: Run** `pytest tests/test_prompts.py -v` → PASS. **Commit (ends Phase 1).**

---

## Task 6: Roles model + built-in roles

**Files:** Create `src/pv/roles/__init__.py`, `model.py`, `builtin/*.yaml`, `tests/test_roles.py`.

- [ ] **Step 1: Implement `roles/model.py`**:
```python
from __future__ import annotations
import yaml
from importlib import resources
from pydantic import BaseModel

class Role(BaseModel):
    name: str
    description: str = ""
    sections: list[str] = []          # required prompt sections
    checklist: list[str] = []         # best-practice checklist for the generator
    repo_analysis: str = "off"        # off | light | deep (default for this role)
    target: str = "raw"               # default export target
    scorers: list[str] = []           # eval defaults (used in later phases)
    playbook: list[str] = []

def list_roles() -> list[str]:
    return sorted(p.name[:-5] for p in resources.files("pv.roles.builtin").iterdir()
                  if p.name.endswith(".yaml"))

def load_role(name: str) -> Role:
    text = (resources.files("pv.roles.builtin") / f"{name}.yaml").read_text()
    return Role(name=name, **yaml.safe_load(text))
```
- [ ] **Step 2: Create the six built-in YAMLs.** Each has `description, sections, checklist, repo_analysis, target, scorers, playbook`. Concrete content:
  - `meeting.yaml`: repo_analysis off, target raw, sections=[Context, Inputs, Agenda structure, Time-boxing, Decisions & action items, Output format], checklist includes "time-box every section", "force decisions + owners", scorers=[llm_judge].
  - `feature_design.yaml`: repo_analysis light, target cursor, sections=[Context, Repo conventions, Reuse audit, Design proposal, Implementation steps, Constraints], checklist includes "inspect repo before designing", "prefer reuse over new code", "follow detected conventions", scorers=[llm_judge].
  - `code_review.yaml`: repo_analysis light, target claude, sections=[Context, What to review, Severity rubric, Legacy risks, Findings format], checklist includes "no behavior change without note", "flag missing tests", "structured findings by severity", scorers=[json_schema_valid, llm_judge].
  - `general.yaml`: repo_analysis off, target raw, generic sections, scorers=[llm_judge].
  - `writer.yaml`: repo_analysis off, target chatgpt, sections=[Audience, Voice, Structure, Constraints, Output], scorers=[llm_judge].
  - `extract.yaml`: repo_analysis off, target raw, sections=[Task, Schema, Rules, Output JSON], checklist "specify exact output schema", scorers=[json_schema_valid, exact_match].
- [ ] **Step 3: Failing test** `tests/test_roles.py`:
```python
from pv.roles.model import list_roles, load_role

def test_builtins_present():
    names = list_roles()
    for r in ["meeting","feature_design","code_review","general","writer","extract"]:
        assert r in names

def test_load_role_fields():
    r = load_role("code_review")
    assert r.repo_analysis in ("off","light","deep")
    assert r.sections and r.checklist and r.playbook
```
- [ ] **Step 4: Ensure `builtin` ships as package data** — add to `pyproject.toml` `[tool.setuptools.package-data] "pv.roles.builtin" = ["*.yaml"]` and `include-package-data`. Reinstall `-e`.
- [ ] **Step 5: Run** `pytest tests/test_roles.py -v` → PASS. **Commit.**

---

## Task 7: Brief + repo analysis

**Files:** Create `src/pv/generate/__init__.py`, `base.py`, `repo_analysis.py`, `tests/test_brief.py`, `tests/test_repo_analysis.py`.

- [ ] **Step 1: Implement `generate/base.py`**:
```python
from __future__ import annotations
from pathlib import Path
from typing import Literal
from pydantic import BaseModel

class Brief(BaseModel):
    idea: str
    role: str
    workflow_notes: str | None = None
    audience: str | None = None
    inputs: list[str] = []
    constraints: list[str] = []
    output_shape: str | None = None
    target: Literal["claude","cursor","chatgpt","raw"] = "raw"
    repo: Path | None = None
    analyze: Literal["off","light","deep"] = "light"
```
- [ ] **Step 2: Implement `generate/repo_analysis.py`**:
```python
from __future__ import annotations
from pathlib import Path
from ..runners.base import Message, GenParams

SCHEMA = {"type":"object","properties":{
    "stack":{"type":"string"},"conventions":{"type":"array","items":{"type":"string"}},
    "reusable":{"type":"array","items":{"type":"string"}},
    "risks":{"type":"array","items":{"type":"string"}}},
    "required":["stack","conventions","reusable","risks"],"additionalProperties":False}

def analyze(runner, repo: Path, depth: str = "light") -> dict | None:
    if depth == "off":
        return None
    scope = ("Skim the manifest and top-level structure only."
             if depth == "light" else
             "Inspect key directories, component/util/test patterns, and risks.")
    msg = (f"Analyze the repository at {repo}. {scope} "
           "Report stack, dominant conventions, reusable modules, and risks.")
    resp = runner.complete(
        [Message(role="user", content=msg)],
        GenParams(model="opus", tools=["Read","Glob","Grep"], json_schema=SCHEMA),
    )
    return resp.structured or None
```
- [ ] **Step 3: Failing tests** — `tests/test_brief.py` (defaults: `analyze=="light"`, `target=="raw"`) and `tests/test_repo_analysis.py`:
```python
from pathlib import Path
from pv.generate.repo_analysis import analyze
from pv.runners.fake_runner import FakeRunner

def test_off_returns_none():
    assert analyze(FakeRunner(), Path("."), "off") is None

def test_light_calls_runner_with_read_tools():
    captured = {}
    def responder(messages, params):
        captured["tools"] = params.tools
        return {"stack":"next.js","conventions":["app router"],"reusable":["Button"],"risks":[]}
    out = analyze(FakeRunner(responder), Path("/x"), "light")
    assert out["stack"] == "next.js"
    assert "Read" in captured["tools"]
```
- [ ] **Step 4: Run** both → PASS. **Commit.**

---

## Task 8: Meta-prompt generator + critique

**Files:** Create `src/pv/generate/meta_prompt.py`, `critique.py`, `tests/test_meta_prompt.py`, `tests/test_critique.py`.

- [ ] **Step 1: Implement `generate/meta_prompt.py`** — builds the meta-prompt, calls runner with a structured schema, returns a `PromptVersion`:
```python
from __future__ import annotations
from ..runners.base import Message, GenParams
from ..roles.model import load_role
from ..prompts.model import PromptVersion
from .base import Brief

GEN_SCHEMA = {"type":"object","properties":{
    "description":{"type":"string"},"system":{"type":"string"},"user":{"type":"string"},
    "rationale":{"type":"string"}},
    "required":["description","system","user","rationale"],"additionalProperties":False}

def build_meta_prompt(brief: Brief, role, repo_summary: dict | None) -> str:
    parts = [
        "You are an expert prompt engineer. Write a high-quality, reusable PROMPT "
        "that another AI will run later. Return JSON matching the schema.",
        f"# Task idea\n{brief.idea}",
        f"# Role: {role.name}\n{role.description}",
        "# Required sections\n" + "\n".join(f"- {s}" for s in role.sections),
        "# Best-practice checklist\n" + "\n".join(f"- {c}" for c in role.checklist),
    ]
    if brief.workflow_notes: parts.append(f"# Workflow\n{brief.workflow_notes}")
    if brief.audience: parts.append(f"# Audience\n{brief.audience}")
    if brief.inputs: parts.append("# Inputs available at use-time (use {placeholders})\n"
                                  + "\n".join(f"- {i}" for i in brief.inputs))
    if brief.constraints: parts.append("# Constraints\n" + "\n".join(f"- {c}" for c in brief.constraints))
    if brief.output_shape: parts.append(f"# Desired output\n{brief.output_shape}")
    if repo_summary: parts.append("# Repo analysis (bake these conventions in)\n" + _fmt_repo(repo_summary))
    parts.append(f"# Target surface\n{brief.target}")
    parts.append("Use {curly_braces} for variables the user fills at run-time. "
                 "The 'system' field is the persona+rules; 'user' is the task template.")
    return "\n\n".join(parts)

def _fmt_repo(s: dict) -> str:
    return (f"Stack: {s.get('stack','')}\nConventions: {', '.join(s.get('conventions',[]))}\n"
            f"Reusable: {', '.join(s.get('reusable',[]))}\nRisks: {', '.join(s.get('risks',[]))}")

def generate(runner, brief: Brief, repo_summary: dict | None = None) -> tuple[PromptVersion, str]:
    role = load_role(brief.role)
    meta = build_meta_prompt(brief, role, repo_summary)
    resp = runner.complete([Message(role="user", content=meta)],
                           GenParams(model="opus", json_schema=GEN_SCHEMA, max_tokens=4096))
    data = resp.structured or {}
    name = _slug(brief.idea)
    pv = PromptVersion(name=name, role=brief.role,
                       description=data.get("description",""),
                       defaults={"model":"opus"},
                       system=data.get("system",""), user=data.get("user",""))
    return pv, data.get("rationale","")

def _slug(text: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+","-", text.lower()).strip("-")[:48] or "prompt"
```
- [ ] **Step 2: Implement `generate/critique.py`**:
```python
from __future__ import annotations
from ..runners.base import Message, GenParams
from ..roles.model import load_role
from ..prompts.model import PromptVersion

CRIT_SCHEMA = {"type":"object","properties":{
    "system":{"type":"string"},"user":{"type":"string"},"changes":{"type":"string"}},
    "required":["system","user","changes"],"additionalProperties":False}

def critique(runner, prompt: PromptVersion) -> tuple[PromptVersion, str]:
    role = load_role(prompt.role) if prompt.role else None
    checklist = "\n".join(f"- {c}" for c in (role.checklist if role else []))
    msg = ("Critique and improve this prompt against the checklist, then return the "
           f"revised system/user and a summary of changes.\n\n# Checklist\n{checklist}\n\n"
           f"# Current system\n{prompt.system}\n\n# Current user\n{prompt.user}")
    resp = runner.complete([Message(role="user", content=msg)],
                           GenParams(model="opus", json_schema=CRIT_SCHEMA))
    d = resp.structured or {}
    revised = prompt.model_copy(update={"system": d.get("system", prompt.system),
                                        "user": d.get("user", prompt.user)})
    return revised, d.get("changes","")
```
- [ ] **Step 3: Failing tests** `tests/test_meta_prompt.py`:
```python
from pv.generate.meta_prompt import build_meta_prompt, generate, _slug
from pv.generate.base import Brief
from pv.roles.model import load_role
from pv.runners.fake_runner import FakeRunner

def test_meta_prompt_includes_role_and_repo():
    b = Brief(idea="design a feature", role="feature_design", inputs=["feature"])
    meta = build_meta_prompt(b, load_role("feature_design"),
                             {"stack":"next.js","conventions":["app router"],"reusable":["Button"],"risks":[]})
    assert "feature_design" in meta and "next.js" in meta and "{placeholders}" in meta or "placeholders" in meta

def test_generate_returns_promptversion():
    def responder(messages, params):
        return {"description":"d","system":"You are X.","user":"Do {feature}","rationale":"r"}
    pv, rationale = generate(FakeRunner(responder), Brief(idea="My MBR agenda!", role="meeting"))
    assert pv.system == "You are X." and "{feature}" in pv.user
    assert pv.name == _slug("My MBR agenda!") and pv.role == "meeting"
    assert rationale == "r"
```
and `tests/test_critique.py`:
```python
from pv.generate.critique import critique
from pv.prompts.model import PromptVersion
from pv.runners.fake_runner import FakeRunner

def test_critique_revises():
    p = PromptVersion(name="x", role="general", system="old", user="old {v}")
    def responder(m,par): return {"system":"new","user":"new {v}","changes":"tightened"}
    revised, changes = critique(FakeRunner(responder), p)
    assert revised.system == "new" and changes == "tightened"
```
- [ ] **Step 4: Run** both → PASS. **Commit.**

---

## Task 9: Exporters

**Files:** Create `src/pv/export/__init__.py`, `base.py`, `claude_skill.py`, `cursor_rules.py`, `chatgpt_gpt.py`, `tests/test_export.py`.

- [ ] **Step 1: Implement `export/base.py`** — `slugify(s)` and an `Exporter` Protocol `export(prompt, out_dir) -> Path`.
- [ ] **Step 2: Implement the three exporters** (pure string formatting → files):
  - `claude_skill.py`: writes `<out>/<slug>/SKILL.md` with YAML frontmatter `name`, `description` (from prompt.description) + the system/user body as instructions. Returns the SKILL.md path.
  - `cursor_rules.py`: writes `<out>/<slug>.mdc` (Cursor rules) with a header and the system+user content. Returns path.
  - `chatgpt_gpt.py`: writes `<out>/<slug>-gpt.md` with "Name / Description / Instructions (system) / Conversation starter (user template)" sections. Returns path.
  - A dispatcher `export(prompt, target, out_dir)` mapping `claude|cursor|chatgpt` → the right exporter.
- [ ] **Step 3: Failing test** `tests/test_export.py`:
```python
from pathlib import Path
from pv.prompts.model import PromptVersion
from pv.export import export

def test_export_targets(tmp_path):
    p = PromptVersion(name="legacy-review", description="Review diffs",
                      system="You are a reviewer.", user="Review {diff}")
    sk = export(p, "claude", tmp_path); assert sk.exists() and sk.name == "SKILL.md"
    cur = export(p, "cursor", tmp_path); assert cur.exists() and cur.suffix == ".mdc"
    gpt = export(p, "chatgpt", tmp_path); assert gpt.exists()
    assert "You are a reviewer." in sk.read_text()
```
- [ ] **Step 4: Run** → PASS. **Commit.**

---

## Task 10: Run ledger (store)

**Files:** Create `src/pv/store/runs.py`, `tests/test_store.py`.

- [ ] **Step 1: Implement `store/runs.py`** — minimal SQLite:
```python
from __future__ import annotations
import sqlite3, json, time
from pathlib import Path

DDL = """CREATE TABLE IF NOT EXISTS runs(
  id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, kind TEXT, name TEXT,
  model TEXT, cost_usd REAL, detail TEXT)"""

class RunStore:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(db_path); self.db.execute(DDL); self.db.commit()
    def record(self, kind, name, model="", cost_usd=0.0, detail=None) -> int:
        cur = self.db.execute("INSERT INTO runs(ts,kind,name,model,cost_usd,detail) VALUES(?,?,?,?,?,?)",
                              (time.time(), kind, name, model, cost_usd, json.dumps(detail or {})))
        self.db.commit(); return cur.lastrowid
    def list(self, limit=50):
        return self.db.execute("SELECT id,kind,name,model,cost_usd FROM runs ORDER BY id DESC LIMIT ?",
                              (limit,)).fetchall()
    def total_cost(self) -> float:
        return self.db.execute("SELECT COALESCE(SUM(cost_usd),0) FROM runs").fetchone()[0]
```
- [ ] **Step 2: Failing test** `tests/test_store.py`:
```python
from pv.store.runs import RunStore

def test_record_and_total(tmp_path):
    s = RunStore(tmp_path/"runs.db")
    s.record("generate","agenda",model="opus",cost_usd=0.02)
    s.record("generate","review",model="opus",cost_usd=0.03)
    assert round(s.total_cost(),2) == 0.05
    assert len(s.list()) == 2
```
- [ ] **Step 3: Run** → PASS. **Commit.**

---

## Task 11: CLI

**Files:** Create `src/pv/cli.py`, `tests/test_cli.py`, `.claude/commands/{new,critique,export}.md`.

- [ ] **Step 1: Implement `cli.py`** with typer. Commands:
  - `new(idea, role="general", repo=None, deep=False, no_analyze=False, target=None, yes=False)`:
    resolve runner via `get_runner()`; build `Brief` (analyze = off if `--no-analyze`, deep if `--deep`, else role default; target = `target` or role.target); if repo & analyze!="off" → `repo_analysis.analyze`; `generate(...)`; save via `PromptStore(library_dir)`; record run; print path + rationale + cost; if target!="raw" auto-export.
  - `prompt list|show|diff|critique`.
  - `export(name, target, out=None)`.
  - `role show <name>` / `role list`.
  - `runs list` (table + cumulative cost).
  - Stubs: `promote`, `init`, `eval`, `optimize`, `distill` → `rich.print("[yellow]coming in a later phase[/]")`.
- [ ] **Step 2: Failing test** `tests/test_cli.py` (uses `typer.testing.CliRunner` + `PV_RUNNER=fake`, runs in `tmp_path` chdir):
```python
import os
from typer.testing import CliRunner
from pv.cli import app

def test_new_generates_into_library(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PV_RUNNER","fake")
    (tmp_path/"pyproject.toml").write_text("[project]\nname='x'\n")  # mark root
    r = CliRunner().invoke(app, ["new","Build an MBR agenda","--role","meeting","--no-analyze"])
    assert r.exit_code == 0, r.output
    libs = list((tmp_path/"library").glob("*/v1.yaml"))
    assert libs, r.output

def test_role_list():
    r = CliRunner().invoke(app, ["role","list"])
    assert r.exit_code == 0 and "meeting" in r.output
```
  (FakeRunner with `json_schema` returns `{"_fake":True}`; ensure `generate` tolerates missing keys → system/user default to "". Add a default responder in the CLI test path OR make FakeRunner return schema-shaped stub. To keep the test meaningful, set `PV_RUNNER=fake` and have `fake_runner` detect a `GEN_SCHEMA`-like schema and return filled fields. Simplest: in `fake_runner`, when `json_schema` has properties `system`&`user`, return those keys with placeholder text. Implement that.)
- [ ] **Step 3: Adjust `fake_runner`** so structured responses fill required string props with `"fake <prop>"` when no responder is given (makes CLI smoke meaningful). Update `tests/test_runner.py` if needed.
- [ ] **Step 4: Write `.claude/commands/{new,critique,export}.md`** — thin wrappers instructing Claude Code to run the corresponding `pv` command with the user's args.
- [ ] **Step 5: Run** `pytest tests/test_cli.py -v` → PASS. **Commit.**

---

## Task 12: Full suite + docs + smoke

- [ ] **Step 1:** `pytest -q` → all green.
- [ ] **Step 2:** Offline end-to-end smoke: `PV_RUNNER=fake pv new "review changes in our legacy repo" --role code_review --no-analyze` in a scratch dir → confirm `library/<slug>/v1.yaml` written and cost line printed.
- [ ] **Step 3:** Update README with the three worked examples and a "Live vs offline (`PV_RUNNER=fake`)" note and the credit-budget caveat.
- [ ] **Step 4:** Commit; open PR-ready branch summary.

---

## Self-review (author)
- **Spec coverage:** runners ✓ (claude subprocess; Agent SDK deferred & noted), cache ✓, prompts ✓, generate (brief/meta/repo-toggle/critique) ✓, roles (6 builtins as playbooks) ✓, export (3 targets) ✓, store/cost ✓, CLI incl. `new` ✓, library storage ✓, `.claude/commands` ✓. Deferred per scope: eval/optimize/distill/promote/init (stubbed), Agent SDK, OpenAI runner.
- **Placeholder scan:** all code steps contain real code; YAML role contents enumerated in Task 6.
- **Type consistency:** `Response`/`GenParams`/`PromptVersion`/`Brief`/`Role` field names consistent across tasks; `get_runner`, `generate`, `critique`, `analyze`, `export`, `PromptStore.save_new_version` signatures match their call sites in the CLI.
