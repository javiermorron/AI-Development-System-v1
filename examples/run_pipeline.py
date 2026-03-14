"""
Example pipeline runner.

Usage:
    python -m examples.run_pipeline
    python -m examples.run_pipeline --feature "Order management with payments and invoices"
    python -m examples.run_pipeline --feature "Blog with posts, comments and tags" --show-code
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich import box

from examples.pipeline import build_example_pipeline
from src.pipeline.stages import StageStatus

console = Console()

DEFAULT_FEATURE = "User authentication system with JWT tokens and role-based permissions"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

@click.command()
@click.option(
    "--feature", "-f",
    default=DEFAULT_FEATURE,
    show_default=True,
    help="Plain-text description of the feature to build.",
)
@click.option(
    "--show-code", is_flag=True, default=False,
    help="Print generated source files after the pipeline completes.",
)
@click.option(
    "--config", "-c",
    default="config_example.yaml",
    show_default=True,
)
def main(feature: str, show_code: bool, config: str) -> None:
    """Run the three-agent example pipeline: architecture -> backend -> reviewer."""
    from src.config import load_config

    cfg = load_config(config)
    engine, context = build_example_pipeline(feature=feature, config=cfg)

    # -- Header --------------------------------------------------------------
    from src.utils import slugify
    output_dir = f"generated/{slugify(feature)}"

    console.print()
    console.print(Panel(
        f"[bold cyan]AI Development System v2[/bold cyan] - Example Pipeline\n\n"
        f"[bold]Feature:[/bold]    {feature}\n"
        f"[bold]Output dir:[/bold] {output_dir}",
        expand=False,
    ))
    console.print()

    # -- Run -----------------------------------------------------------------
    results = engine.run(context)

    # -- Print stage results --------------------------------------------------
    for stage_result in results:
        name = stage_result.stage_name.upper()

        if stage_result.status == StageStatus.FAILED:
            console.print(Panel(
                f"[red]FAILED[/red]  {stage_result.error}",
                title=f"[red]>> {name}[/red]",
                border_style="red",
            ))
            console.print("\n[red]Pipeline aborted.[/red]")
            sys.exit(1)

        output = stage_result.output or {}

        if stage_result.stage_name == "architecture":
            _print_architecture(output)
        elif stage_result.stage_name == "backend":
            _print_backend(output, show_code)
        elif stage_result.stage_name == "reviewer":
            _print_reviewer(output)

    # -- Final verdict --------------------------------------------------------
    reviewer_out = context.stage_outputs.get("reviewer", {})
    approved = reviewer_out.get("approved", False)
    score = reviewer_out.get("score", 0)

    console.print()
    if approved:
        console.print(Panel(
            f"[green bold]OK PIPELINE PASSED[/green bold]\n"
            f"Score: {score}/10   All stages completed successfully.\n\n"
            f"[bold]Output:[/bold] [cyan]{output_dir}/[/cyan]\n\n"
            f"[bold]To run:[/bold]\n"
            f"  cd {output_dir}\n"
            f"  pip install -r requirements.txt\n"
            f"  uvicorn main:app --reload\n\n"
            f"Then open http://localhost:8000/docs",
            border_style="green",
        ))
    else:
        console.print(Panel(
            f"[yellow bold]! PIPELINE COMPLETED WITH WARNINGS[/yellow bold]\n"
            f"Score: {score}/10   Review the findings above before proceeding.\n\n"
            f"[bold]Output:[/bold] [cyan]{output_dir}/[/cyan]",
            border_style="yellow",
        ))


# ---------------------------------------------------------------------------
# Per-stage display helpers
# ---------------------------------------------------------------------------

def _print_architecture(output: dict) -> None:
    entities   = output.get("entities", [])
    components = output.get("components", [])
    routes     = output.get("routes", [])
    concerns   = output.get("security_concerns", [])

    content_lines = [
        f"[bold]Entities[/bold]   : {', '.join(entities)}",
        f"[bold]Components[/bold] : {', '.join(components)}",
        f"[bold]Routes[/bold]     : {len(routes)} endpoints across {len(entities)} resource(s)",
    ]
    if concerns:
        content_lines.append(
            f"[bold]Security[/bold]   : {len(concerns)} concern(s) identified"
        )

    console.print(Panel(
        "\n".join(content_lines),
        title="[green]>> ARCHITECTURE[/green]",
        border_style="green",
    ))

    # Route table
    route_table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    route_table.add_column("Method",  style="cyan",   min_width=8)
    route_table.add_column("Path",    min_width=28)
    route_table.add_column("Handler", min_width=22)
    route_table.add_column("Level",   min_width=6)

    level_colors = {1: "green", 2: "yellow", 3: "red"}
    for r in routes:
        lvl = r["security_level"]
        color = level_colors.get(lvl, "white")
        route_table.add_row(
            r["method"], r["path"], r["handler"],
            f"[{color}]{lvl}[/{color}]",
        )
    console.print(route_table)

    if concerns:
        console.print("  [bold]Security concerns:[/bold]")
        for c in concerns:
            console.print(f"    [yellow]![/yellow] {c}")
    console.print()


def _print_backend(output: dict, show_code: bool) -> None:
    files     = output.get("files", {})
    entities  = output.get("entities_implemented", [])
    loc       = output.get("lines_of_code", 0)
    n_routes  = output.get("route_count", 0)

    # Group files for display
    top_level = sorted(f for f in files if "/" not in f)
    routers   = sorted(f for f in files if f.startswith("routers/"))

    tree_lines = [f"  [cyan]{f}[/cyan]" for f in top_level]
    if routers:
        tree_lines.append("  [cyan]routers/[/cyan]")
        for r in routers:
            tree_lines.append(f"    [cyan]{r.split('/')[-1]}[/cyan]")

    console.print(Panel(
        f"[bold]Entities[/bold] : {', '.join(entities)}\n"
        f"[bold]Routes[/bold]   : {n_routes} FastAPI handler stubs\n"
        f"[bold]Lines[/bold]    : ~{loc} lines of Python\n\n"
        "[bold]Files generated:[/bold]\n" + "\n".join(tree_lines),
        title="[green]>> BACKEND[/green]",
        border_style="green",
    ))

    if show_code:
        for filename, code in files.items():
            console.print(Panel(
                Syntax(code, "python", theme="monokai", line_numbers=True),
                title=f"[cyan]{filename}[/cyan]",
                border_style="dim",
            ))
    console.print()


def _print_reviewer(output: dict) -> None:
    approved = output.get("approved", False)
    score    = output.get("score", 0)
    summary  = output.get("summary", "")
    findings = output.get("findings", [])
    metrics  = output.get("metrics", {})

    verdict_color = "green" if approved else "yellow"
    verdict_str   = "APPROVED" if approved else "NEEDS WORK"

    console.print(Panel(
        f"[{verdict_color} bold]{verdict_str}[/{verdict_color} bold]  "
        f"Score: [bold]{score}/10[/bold]\n\n"
        f"{summary}\n\n"
        f"[bold]Files reviewed    :[/bold] {metrics.get('files_reviewed', 0)}\n"
        f"[bold]Classes found     :[/bold] {metrics.get('classes_found', 0)}\n"
        f"[bold]Functions found   :[/bold] {metrics.get('functions_found', 0)}\n"
        f"[bold]Docstring coverage:[/bold] {metrics.get('docstring_coverage', 'n/a')}\n"
        f"[bold]Stubs (NotImpl)   :[/bold] {metrics.get('not_implemented_count', 0)}\n"
        f"[bold]TODO comments     :[/bold] {metrics.get('todo_count', 0)}",
        title="[green]>> REVIEWER[/green]",
        border_style=verdict_color,
    ))

    if findings:
        severity_order = {"ERROR": 0, "WARNING": 1, "INFO": 2}
        sorted_findings = sorted(findings, key=lambda f: severity_order.get(f["severity"], 3))

        findings_table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
        findings_table.add_column("Severity", min_width=10)
        findings_table.add_column("File",     style="cyan", min_width=16)
        findings_table.add_column("Line",     min_width=5)
        findings_table.add_column("Message")

        sev_colors = {"ERROR": "red", "WARNING": "yellow", "INFO": "dim"}
        for f in sorted_findings:
            color = sev_colors.get(f["severity"], "white")
            findings_table.add_row(
                f"[{color}]{f['severity']}[/{color}]",
                f["file"],
                str(f["line"]) if f["line"] else "-",
                f["message"],
            )
        console.print(findings_table)

    console.print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    main()
