"""The `pv` command-line interface."""

from __future__ import annotations

import difflib
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich import print as rprint
from rich.console import Console
from rich.table import Table

from .export import export as export_prompt
from .generate.base import Brief
from .generate.critique import critique as critique_prompt
from .generate.meta_prompt import generate as generate_prompt
from .generate.repo_analysis import analyze as analyze_repo
from .prompts.registry import PromptStore
from .roles.model import list_roles, load_role
from .runners.cache import ResponseCache
from .runners.caching import CachingRunner
from .runners.metering import MeteringRunner
from .runners.registry import get_runner
from .store import paths
from .store.runs import RunStore

app = typer.Typer(
    help="Prompt Vishwakarma — generate & improve prompts, key-free via Claude Code.",
    no_args_is_help=True,
)
role_app = typer.Typer(help="Inspect role playbooks.", no_args_is_help=True)
prompt_app = typer.Typer(help="Manage prompt versions.", no_args_is_help=True)
runs_app = typer.Typer(help="Inspect the local run ledger.", no_args_is_help=True)
app.add_typer(role_app, name="role")
app.add_typer(prompt_app, name="prompt")
app.add_typer(runs_app, name="runs")

console = Console()


@contextmanager
def _bad_param_on_missing():
    try:
        yield
    except FileNotFoundError as e:
        raise typer.BadParameter(str(e))


def _store() -> PromptStore:
    return PromptStore(paths.library_dir(paths.repo_root()))


def _runs() -> RunStore:
    return RunStore(paths.runs_db(paths.repo_root()))


def _runner(no_cache: bool = False) -> MeteringRunner:
    inner = get_runner()
    if no_cache:
        return MeteringRunner(inner)
    cache = ResponseCache(paths.cache_dir(paths.repo_root()))
    return MeteringRunner(CachingRunner(inner, cache))


def _cost_line(runner: MeteringRunner) -> str:
    return f"[dim]cost: ${runner.total_cost:.4f} ({runner.n_calls} call(s))[/]"


@app.command()
def new(
    idea: str = typer.Argument(..., help="The core idea / task for the prompt."),
    role: str = typer.Option("general", "--role", "-r", help="Prompt-category playbook."),
    repo: Optional[Path] = typer.Option(None, "--repo", help="Repo to ground the prompt in."),
    deep: bool = typer.Option(False, "--deep", help="Thorough repo analysis."),
    no_analyze: bool = typer.Option(False, "--no-analyze", help="Skip repo analysis."),
    target: Optional[str] = typer.Option(
        None, "--target", help="Auto-export target: claude|cursor|chatgpt|raw."
    ),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass the response cache."),
):
    """Generate a prompt from a brief into the library."""
    with _bad_param_on_missing():
        role_obj = load_role(role)
    if repo is not None:
        if not repo.is_dir():
            raise typer.BadParameter(f"repo not found: {repo}")
        repo = repo.resolve()

    if no_analyze:
        analyze_mode = "off"
    elif deep:
        analyze_mode = "deep"
    else:
        analyze_mode = role_obj.repo_analysis
    tgt = target or role_obj.target

    runner = _runner(no_cache)
    try:
        repo_summary = None
        if repo is not None and analyze_mode != "off":
            rprint(f"[dim]Analyzing repo ({analyze_mode}) …[/]")
            repo_summary = analyze_repo(runner, repo, analyze_mode)
        brief = Brief(idea=idea, role=role, target=tgt, repo=repo, analyze=analyze_mode)
        prompt, rationale = generate_prompt(runner, brief, repo_summary)
    except Exception as e:  # surface engine errors cleanly, not as a traceback
        rprint(f"[red]generation failed:[/] {e}")
        raise typer.Exit(1)

    root = paths.repo_root()
    saved = _store().save_new_version(prompt)
    _write_brief(paths.library_dir(root) / saved.name / "brief.yaml", brief)
    with _runs() as runs:
        runs.record(
            "generate",
            saved.name,
            model=runner.last_model or "opus",
            cost_usd=runner.total_cost,
            detail={"role": role, "target": tgt, "analyze": analyze_mode},
        )

    rel = f"library/{saved.name}/v{saved.version}.yaml"
    rprint(f"[green]✓[/] generated [bold]{saved.name}[/] v{saved.version} → {rel}")
    if rationale:
        rprint(f"[dim]rationale:[/] {rationale}")
    if tgt != "raw":
        out_dir = paths.ensure(paths.library_dir(root) / saved.name / "exports")
        out_path = export_prompt(saved, tgt, out_dir)
        rprint(f"[green]✓[/] exported ({tgt}) → {out_path}")
    rprint(_cost_line(runner))


def _write_brief(path: Path, brief: Brief) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(brief.model_dump(mode="json"), sort_keys=False))


@app.command()
def export(
    name: str = typer.Argument(..., help="Prompt name in the library."),
    target: str = typer.Option(..., "--target", help="claude|cursor|chatgpt."),
    out: Optional[Path] = typer.Option(None, "--out", help="Output directory."),
):
    """Export a library prompt as a portable artifact."""
    with _bad_param_on_missing():
        prompt = _store().load(name)
    out_dir = out or (paths.library_dir(paths.repo_root()) / name / "exports")
    paths.ensure(Path(out_dir))
    path = export_prompt(prompt, target, Path(out_dir))
    rprint(f"[green]✓[/] exported ({target}) → {path}")


# ---- prompt sub-app ----------------------------------------------------------


@prompt_app.command("list")
def prompt_list():
    names = _store().list()
    if not names:
        rprint("[dim](no prompts in library yet — try `pv new`)[/]")
        return
    for n in names:
        rprint(n)


@prompt_app.command("show")
def prompt_show(
    name: str = typer.Argument(...),
    version: Optional[int] = typer.Option(None, "--version", "-v"),
):
    with _bad_param_on_missing():
        p = _store().load(name, version)
    rprint(f"[bold]{p.name}[/] v{p.version}  (role: {p.role})")
    rprint(f"[dim]{p.description}[/]\n")
    rprint("[bold]system[/]\n" + p.system + "\n")
    rprint("[bold]user[/]\n" + p.user)


@prompt_app.command("diff")
def prompt_diff(
    name: str = typer.Argument(...),
    v1: int = typer.Argument(...),
    v2: int = typer.Argument(...),
):
    with _bad_param_on_missing():
        store = _store()
        a = store.load(name, v1)
        b = store.load(name, v2)
    a_text = f"{a.system}\n---\n{a.user}".splitlines(keepends=True)
    b_text = f"{b.system}\n---\n{b.user}".splitlines(keepends=True)
    diff = difflib.unified_diff(a_text, b_text, fromfile=f"v{v1}", tofile=f"v{v2}")
    console.print("".join(diff) or "[dim](identical)[/]")


@prompt_app.command("critique")
def prompt_critique(
    name: str = typer.Argument(...),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass the response cache."),
):
    """Single-shot critique → a new improved version."""
    store = _store()
    with _bad_param_on_missing():
        current = store.load(name)
    runner = _runner(no_cache)
    try:
        revised, changes = critique_prompt(runner, current)
    except Exception as e:
        rprint(f"[red]critique failed:[/] {e}")
        raise typer.Exit(1)
    saved = store.save_new_version(revised)
    with _runs() as runs:
        runs.record("critique", name, model=runner.last_model or "opus", cost_usd=runner.total_cost)
    rprint(f"[green]✓[/] critiqued [bold]{name}[/] → v{saved.version}")
    if changes:
        rprint(f"[dim]changes:[/] {changes}")
    rprint(_cost_line(runner))


# ---- role sub-app ------------------------------------------------------------


@role_app.command("list")
def role_list():
    for r in list_roles():
        rprint(r)


@role_app.command("show")
def role_show(name: str = typer.Argument(...)):
    with _bad_param_on_missing():
        r = load_role(name)
    rprint(f"[bold]{r.name}[/] — {r.description}")
    rprint(f"[dim]repo_analysis:[/] {r.repo_analysis}   [dim]target:[/] {r.target}")
    rprint("\n[bold]sections[/]\n" + "\n".join(f"  - {s}" for s in r.sections))
    rprint("\n[bold]checklist[/]\n" + "\n".join(f"  - {c}" for c in r.checklist))
    rprint("\n[bold]playbook[/]\n" + "\n".join(f"  {i+1}. {p}" for i, p in enumerate(r.playbook)))


# ---- runs sub-app ------------------------------------------------------------


@runs_app.command("list")
def runs_list(limit: int = typer.Option(50, "--limit")):
    with _runs() as store:
        rows = store.list(limit)
        total = store.total_cost()
    table = Table("id", "kind", "name", "model", "cost ($)")
    for rid, kind, name, model, cost in rows:
        table.add_row(str(rid), kind, name, model, f"{cost:.4f}")
    console.print(table)
    rprint(f"[bold]total cost:[/] ${total:.4f}")


# ---- stubs (later phases) ----------------------------------------------------


def _stub(phase: str):
    rprint(f"[yellow]Not built yet — coming in {phase}.[/]")
    raise typer.Exit(0)


@app.command()
def promote(name: str = typer.Argument(...), to_project: str = typer.Option(..., "--to-project")):
    """(Phase 3) Graduate a library prompt into a full project."""
    _stub("Phase 3 (eval)")


@app.command()
def init(name: str = typer.Argument(...), role: str = typer.Option("general", "--role")):
    """(Phase 3) Scaffold a full project."""
    _stub("Phase 3 (eval)")


@app.command(name="eval")
def eval_(project: str = typer.Option(..., "--project")):
    """(Phase 3) Evaluate a prompt over a dataset."""
    _stub("Phase 3 (eval)")


@app.command()
def optimize(project: str = typer.Option(..., "--project")):
    """(Phase 4) Auto-improve a prompt."""
    _stub("Phase 4 (optimize)")


@app.command()
def distill(project: str = typer.Option(..., "--project")):
    """(Phase 5) Generate fine-tune-ready data."""
    _stub("Phase 5 (distill)")


if __name__ == "__main__":
    app()
