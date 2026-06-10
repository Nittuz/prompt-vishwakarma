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

from .datasets import io as data_io
from .eval.harness import run_eval
from .eval.report import compare as compare_runs
from .eval.report import render_report
from .eval.result import Run
from .eval.scorers import build_scorers
from .export import export as export_prompt
from .generate.base import Brief
from .generate.critique import critique as critique_prompt
from .generate.datagen import gen_examples
from .generate.meta_prompt import generate as generate_prompt
from .generate.repo_analysis import analyze as analyze_repo
from .projects import store as projects
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
data_app = typer.Typer(help="Manage project datasets.", no_args_is_help=True)
app.add_typer(role_app, name="role")
app.add_typer(prompt_app, name="prompt")
app.add_typer(runs_app, name="runs")
app.add_typer(data_app, name="data")

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


# ---- projects: init / promote ------------------------------------------------


@app.command()
def init(
    name: str = typer.Argument(..., help="Project name."),
    role: str = typer.Option("general", "--role", "-r"),
):
    """Scaffold a full project under projects/<name>/."""
    root = paths.repo_root()
    if projects.exists(root, name):
        raise typer.BadParameter(f"project {name!r} already exists")
    with _bad_param_on_missing():
        load_role(role)  # validate
    projects.init_project(root, name, role)
    rprint(f"[green]✓[/] created project [bold]{name}[/] → projects/{name}/ (role: {role})")
    rprint("[dim]next: add a prompt (`pv promote <lib-prompt> --to-project " f"{name}`),[/]")
    rprint(f"[dim]      add examples to projects/{name}/datasets/dev.jsonl, then `pv eval`[/]")


@app.command()
def promote(
    name: str = typer.Argument(..., help="Library prompt name."),
    to_project: str = typer.Option(..., "--to-project"),
):
    """Graduate a library prompt into a project (creating it if needed)."""
    root = paths.repo_root()
    with _bad_param_on_missing():
        project = projects.promote(root, name, to_project)
    rprint(f"[green]✓[/] promoted [bold]{name}[/] → project [bold]{project.name}[/]")
    rprint(f"[dim]prompt copied to projects/{project.name}/prompts/{name}/[/]")


# ---- data sub-app ------------------------------------------------------------


def _load_project_or_exit(name: str):
    with _bad_param_on_missing():
        return projects.load_project(paths.repo_root(), name)


@data_app.command("validate")
def data_validate(
    project: str = typer.Option(..., "--project"),
    split: str = typer.Option("dev", "--split"),
):
    root = paths.repo_root()
    proj = _load_project_or_exit(project)
    examples = data_io.load_jsonl(projects.dataset_path(root, proj, split))
    problems = data_io.validate(examples)
    if problems:
        for p in problems:
            rprint(f"[red]✗[/] {p}")
        raise typer.Exit(1)
    rprint(f"[green]✓[/] {split}: {len(examples)} examples, no problems")


@data_app.command("stats")
def data_stats(
    project: str = typer.Option(..., "--project"),
    split: str = typer.Option("dev", "--split"),
):
    root = paths.repo_root()
    proj = _load_project_or_exit(project)
    examples = data_io.load_jsonl(projects.dataset_path(root, proj, split))
    s = data_io.stats(examples)
    rprint(f"[bold]{project}/{split}[/]: {s['count']} examples, "
           f"{s['with_reference']} with reference")
    for field, n in s["input_fields"].items():
        rprint(f"  [dim]{field}[/]: {n}")


@data_app.command("gen")
def data_gen(
    project: str = typer.Option(..., "--project"),
    n: int = typer.Option(5, "--n"),
    split: str = typer.Option("dev", "--split"),
    no_cache: bool = typer.Option(False, "--no-cache"),
):
    """Synthesize seed examples with Claude and append to a split (curate after)."""
    root = paths.repo_root()
    proj = _load_project_or_exit(project)
    prompt = _resolve_project_prompt(root, project)
    runner = _runner(no_cache)
    try:
        examples = gen_examples(runner, prompt, n=n, model=proj.models.get("primary", "opus"))
    except Exception as e:
        rprint(f"[red]data gen failed:[/] {e}")
        raise typer.Exit(1)
    path = projects.dataset_path(root, proj, split)
    data_io.append_jsonl(path, examples)
    with _runs() as runs:
        runs.record("datagen", project, model=runner.last_model or "opus", cost_usd=runner.total_cost)
    rprint(f"[green]✓[/] generated {len(examples)} examples → {split} ({path})")
    rprint("[yellow]review/curate them before evaluating[/]")
    rprint(_cost_line(runner))


# ---- eval --------------------------------------------------------------------


def _resolve_project_prompt(root: Path, project: str, prompt_name: Optional[str] = None):
    store = projects.prompt_store_for(root, project)
    names = store.list()
    if not names:
        raise typer.BadParameter(
            f"project {project!r} has no prompt — `pv promote <lib-prompt> --to-project {project}`"
        )
    if prompt_name is None:
        if len(names) > 1:
            raise typer.BadParameter(
                f"project has multiple prompts {names}; pass --prompt-name"
            )
        prompt_name = names[0]
    with _bad_param_on_missing():
        return store.load(prompt_name)


@app.command(name="eval")
def eval_(
    project: str = typer.Option(..., "--project"),
    prompt_name: Optional[str] = typer.Option(None, "--prompt-name"),
    version: Optional[int] = typer.Option(None, "--version", "-v"),
    model: Optional[str] = typer.Option(None, "--model"),
    split: str = typer.Option("dev", "--split"),
    no_cache: bool = typer.Option(False, "--no-cache"),
):
    """Evaluate a project's prompt over a dataset split → report + ledger entry."""
    root = paths.repo_root()
    proj = _load_project_or_exit(project)
    prompt = _resolve_project_prompt(root, project, prompt_name)
    if version is not None:
        prompt = projects.prompt_store_for(root, project).load(prompt.name, version)
    examples = data_io.load_jsonl(projects.dataset_path(root, proj, split))
    if not examples:
        raise typer.BadParameter(f"no examples in {split} split — add some first")

    runner = _runner(no_cache)
    scorers = build_scorers(proj.scorers, runner=runner, judge_model=proj.models.get("judge", "opus"))
    use_model = model or proj.models.get("primary", "opus")
    try:
        run = run_eval(runner, prompt, examples, scorers, model=use_model, project=project, split=split)
    except Exception as e:
        rprint(f"[red]eval failed:[/] {e}")
        raise typer.Exit(1)

    run_dir = paths.ensure(projects.project_dir(root, project) / "runs" / run.run_id)
    (run_dir / "run.json").write_text(run.model_dump_json(indent=2))
    (run_dir / "report.md").write_text(render_report(run))
    with _runs() as runs:
        runs.record("eval", project, model=run.model, cost_usd=run.total_cost_usd,
                    detail={"run_id": run.run_id, "split": split})

    table = Table("scorer", "mean", "pass rate")
    for name, m in run.metrics.items():
        table.add_row(name, f"{m['mean']:.3f}", f"{m['pass_rate']:.0%}")
    console.print(table)
    rprint(f"[green]✓[/] {run.run_id} → projects/{project}/runs/{run.run_id}/report.md")
    rprint(_cost_line(runner))


@runs_app.command("compare")
def runs_compare(run_id_a: str = typer.Argument(...), run_id_b: str = typer.Argument(...)):
    """Compare two eval runs by id."""
    root = paths.repo_root()
    a = _find_run(root, run_id_a)
    b = _find_run(root, run_id_b)
    if a is None or b is None:
        missing = run_id_a if a is None else run_id_b
        raise typer.BadParameter(f"run not found: {missing}")
    console.print(compare_runs(a, b))


def _find_run(root: Path, run_id: str) -> Optional[Run]:
    matches = list(paths.projects_dir(root).glob(f"*/runs/{run_id}/run.json"))
    if not matches:
        return None
    return Run.model_validate_json(matches[0].read_text())


# ---- stubs (later phases) ----------------------------------------------------


def _stub(phase: str):
    rprint(f"[yellow]Not built yet — coming in {phase}.[/]")
    raise typer.Exit(0)


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
