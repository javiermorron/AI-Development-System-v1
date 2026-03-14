"""
AI Development System v2 — Command Line Interface

Commands:
    aidev init <project-name>           Generate a new AI-native project scaffold
    aidev pipeline run                  Run the full development pipeline
    aidev pipeline stages               List configured pipeline stages
    aidev agent list                    Show registered agents
    aidev agent run <agent> <task>      Run a single agent task
    aidev audit show                    Display recent audit log entries
    aidev security classify <action>    Classify an action's security level
    aidev security check-prompt <text>  Check a prompt for injection patterns
    aidev example run                   Run the 3-agent example pipeline

Run `aidev --help` or `aidev <command> --help` for details.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from .config import load_config
from .audit.logger import AuditLogger
from .agents.orchestrator import AgentOrchestrator, OrchestrationPlan
from .agents.base import AgentTask
from .pipeline.engine import PipelineEngine, PipelineContext
from .security.classifier import ActionClassifier
from .security.sanitizer import PromptSanitizer

# Import built-in agents so they self-register via @register
from .agents import builtin as _builtin  # noqa: F401

console = Console()


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_audit(config: dict) -> AuditLogger:
    return AuditLogger(
        log_file=config.get("audit", {}).get("log_file", "logs/audit.jsonl"),
        include_inputs=config.get("audit", {}).get("include_inputs", True),
        include_outputs=config.get("audit", {}).get("include_outputs", True),
    )


# ── Root group ─────────────────────────────────────────────────────────────────

@click.group()
@click.version_option("2.0.0", prog_name="aidev")
def cli() -> None:
    """AI Development System v2 — AI-native development framework."""


# ── init ──────────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("project_name")
@click.option(
    "--output", "-o",
    default=".",
    show_default=True,
    help="Parent directory for the generated project.",
)
def init(project_name: str, output: str) -> None:
    """Generate a new AI-native project scaffold."""
    from .generator.generator import ProjectGenerator

    output_path = Path(output).resolve()
    console.print(f"[bold]Creating project:[/bold] [cyan]{project_name}[/cyan]")
    ProjectGenerator().generate(project_name, output_path)
    target = output_path / project_name
    console.print(f"[green]✓[/green] Project created at: {target}\n")
    console.print("[bold]Next steps:[/bold]")
    console.print(f"  1. Fill in  [cyan]{target / 'docs' / 'spec.md'}[/cyan]")
    console.print(f"  2. Complete [cyan]{target / 'docs' / 'threat-model.md'}[/cyan]")
    console.print(f"  3. Implement agents in [cyan]{target / 'agents'}[/cyan]")
    console.print(f"  4. Run: [cyan]aidev pipeline run --config config.yaml[/cyan]")


# ── pipeline ──────────────────────────────────────────────────────────────────

@cli.group()
def pipeline() -> None:
    """Pipeline management commands."""


@pipeline.command("run")
@click.option("--config", "-c", default="config_example.yaml", show_default=True)
@click.option("--project", "-p", default="my-project", show_default=True)
@click.option("--workspace", "-w", default=".", show_default=True)
def pipeline_run(config: str, project: str, workspace: str) -> None:
    """Run the AI development pipeline for a project."""
    cfg = load_config(config)
    audit = _make_audit(cfg)
    engine = PipelineEngine(cfg, audit)
    ctx = PipelineContext(
        project_name=project,
        config=cfg,
        workspace=Path(workspace).resolve(),
    )

    console.print(f"\n[bold]Pipeline[/bold] → project: [cyan]{project}[/cyan]")
    console.rule()

    results = engine.run(ctx)

    table = Table(title="Pipeline Results", show_lines=True)
    table.add_column("Stage", style="cyan", min_width=20)
    table.add_column("Status", min_width=10)
    table.add_column("Details")

    all_passed = True
    for r in results:
        if r.status.value == "passed":
            status_cell = "[green]PASSED[/green]"
        elif r.status.value == "failed":
            status_cell = "[red]FAILED[/red]"
            all_passed = False
        else:
            status_cell = "[yellow]SKIPPED[/yellow]"
            all_passed = False

        detail = (r.error or str(r.output or ""))[:80]
        table.add_row(r.stage_name, status_cell, detail)

    console.print(table)

    if all_passed:
        console.print("\n[green]✓ Pipeline completed successfully.[/green]")
    else:
        console.print("\n[red]✗ Pipeline did not fully complete — see above.[/red]")
        sys.exit(1)


@pipeline.command("stages")
@click.option("--config", "-c", default="config_example.yaml", show_default=True)
def pipeline_stages(config: str) -> None:
    """List the pipeline stages configured in the config file."""
    cfg = load_config(config)
    stages = cfg.get("pipeline", {}).get("stages", [])
    if not stages:
        console.print("[yellow]No stages found in config.[/yellow]")
        return
    console.print("[bold]Configured stages:[/bold]")
    for i, s in enumerate(stages, 1):
        console.print(f"  {i:2}. {s}")


# ── agent ─────────────────────────────────────────────────────────────────────

@cli.group()
def agent() -> None:
    """Agent management commands."""


@agent.command("list")
@click.option("--config", "-c", default="config_example.yaml", show_default=True)
def agent_list(config: str) -> None:
    """List all registered agents and their allowed tools."""
    from .agents.registry import list_agents

    cfg = load_config(config)
    agents = list_agents()
    if not agents:
        console.print("[yellow]No agents registered.[/yellow]")
        console.print(
            "Import agent modules in your entry point or implement agents "
            "in a project's agents/ directory."
        )
        return

    table = Table(title="Registered Agents", show_lines=True)
    table.add_column("Agent", style="cyan")
    table.add_column("Allowed Tools")

    allowed_tools_cfg = cfg.get("agents", {}).get("allowed_tools", {})
    for name in agents:
        tools = allowed_tools_cfg.get(name, [])
        table.add_row(name, ", ".join(tools) if tools else "[dim]not configured[/dim]")

    console.print(table)


@agent.command("run")
@click.argument("agent_name")
@click.argument("task_name")
@click.option("--config", "-c", default="config_example.yaml", show_default=True)
@click.option(
    "--input", "-i", "input_str",
    default="{}",
    show_default=True,
    help="Task input as a JSON object string.",
)
def agent_run(agent_name: str, task_name: str, config: str, input_str: str) -> None:
    """Run a single agent task.

    \b
    Examples:
        aidev agent run backend-agent implement --input '{"spec": "Build a login API"}'
        aidev agent run testing-agent generate-tests
    """
    cfg = load_config(config)
    audit = _make_audit(cfg)

    try:
        task_input: dict = json.loads(input_str)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Invalid JSON input:[/red] {exc}")
        sys.exit(1)

    orchestrator = AgentOrchestrator(cfg, audit)
    task = AgentTask(name=task_name, input=task_input)
    plan = OrchestrationPlan(tasks=[(agent_name, task)])

    console.print(
        f"Running [cyan]{agent_name}[/cyan] → task: [cyan]{task_name}[/cyan]"
    )
    results = orchestrator.run_plan(plan)

    for r in results:
        if r.success:
            console.print(f"[green]✓[/green] {r.output}")
        else:
            console.print(f"[red]✗[/red] {r.error}")
            sys.exit(1)


# ── audit ─────────────────────────────────────────────────────────────────────

@cli.group()
def audit() -> None:
    """Audit log commands."""


@audit.command("show")
@click.option("--config", "-c", default="config_example.yaml", show_default=True)
@click.option("--tail", "-n", default=20, show_default=True, help="Number of recent entries.")
@click.option("--agent", default=None, help="Filter entries by agent name.")
def audit_show(config: str, tail: int, agent: str | None) -> None:
    """Display recent audit log entries."""
    cfg = load_config(config)
    log = _make_audit(cfg)
    entries = log.read_log()

    if agent:
        entries = [e for e in entries if e.get("agent") == agent]

    entries = entries[-tail:]

    if not entries:
        console.print("[yellow]No audit log entries found.[/yellow]")
        return

    table = Table(title=f"Audit Log — last {tail} entries", show_lines=True)
    table.add_column("Timestamp", style="dim", min_width=19)
    table.add_column("Agent", style="cyan")
    table.add_column("Tool")
    table.add_column("OK")
    table.add_column("Output / Error", max_width=55)

    for e in entries:
        ok = "[green]✓[/green]" if e.get("success") else "[red]✗[/red]"
        out = str(e.get("output") or e.get("error") or "")[:55]
        table.add_row(
            str(e.get("timestamp", ""))[:19],
            e.get("agent", ""),
            e.get("tool", ""),
            ok,
            out,
        )

    console.print(table)


# ── security ──────────────────────────────────────────────────────────────────

@cli.group()
def security() -> None:
    """Security utility commands."""


@security.command("classify")
@click.argument("action")
def security_classify(action: str) -> None:
    """Classify an action's security level (1 = Safe, 2 = Sensitive, 3 = Critical)."""
    clf = ActionClassifier()
    level = clf.classify(action)
    desc = clf.describe(action)
    color = {"SAFE": "green", "SENSITIVE": "yellow", "CRITICAL": "red"}[level.name]
    console.print(f"Action : [cyan]{action}[/cyan]")
    console.print(f"Level  : [{color}]{desc}[/{color}]")


@security.command("check-prompt")
@click.argument("prompt")
def security_check_prompt(prompt: str) -> None:
    """Check a prompt string for injection patterns."""
    san = PromptSanitizer()
    if san.is_safe(prompt):
        console.print("[green]✓ Prompt appears safe — no injection patterns detected.[/green]")
    else:
        patterns = san.detected_patterns(prompt)
        console.print("[red]✗ Injection patterns detected:[/red]")
        for p in patterns:
            console.print(f"  • {p}")
        sanitized = san.sanitize(prompt)
        console.print(f"\n[yellow]Sanitized prompt:[/yellow] {sanitized}")


# ── example ───────────────────────────────────────────────────────────────────

@cli.group()
def example() -> None:
    """Example pipelines demonstrating the framework."""


@example.command("run")
@click.option(
    "--feature", "-f",
    default="User authentication system with JWT tokens and role-based permissions",
    show_default=True,
    help="Feature description to pass through the pipeline.",
)
@click.option("--show-code", is_flag=True, default=False,
              help="Print the generated Python source files.")
@click.option("--config", "-c", default="config_example.yaml", show_default=True)
def example_run(feature: str, show_code: bool, config: str) -> None:
    """Run the three-agent example pipeline: architecture → backend → reviewer."""
    # Delegate to the standalone runner (avoids duplicating display logic)
    from click.testing import CliRunner as _  # noqa: F401 — ensure click is available
    from examples.run_pipeline import main as _example_main
    ctx = click.get_current_context()
    ctx.invoke(_example_main, feature=feature, show_code=show_code, config=config)


if __name__ == "__main__":
    cli()
