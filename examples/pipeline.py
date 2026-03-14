"""
ExamplePipeline — wires ArchitectureAgent → BackendAgent → ReviewerAgent
using the existing PipelineEngine + Stage infrastructure.

Data flows through PipelineContext.stage_outputs:
    stage_outputs["architecture"]  ← ArchitectureAgent output
    stage_outputs["backend"]       ← BackendAgent output (reads architecture)
    stage_outputs["reviewer"]      ← ReviewerAgent output (reads backend)

Each stage creates its own agent instance, runs it, and stores the result.
The audit logger is threaded through PipelineContext.metadata["audit"].
"""

from __future__ import annotations

from pathlib import Path

from src.agents.base import AgentTask
from src.audit.logger import AuditLogger
from src.config import load_config
from src.pipeline.engine import PipelineContext, PipelineEngine
from src.pipeline.stages import Stage, StageResult, StageStatus

# Force registration of all three example agents
import examples.agents  # noqa: F401


# ---------------------------------------------------------------------------
# Stage handlers
# ---------------------------------------------------------------------------

def _stage_architecture(ctx: PipelineContext) -> StageResult:
    from examples.agents.architecture_agent import ArchitectureAgent

    feature: str = ctx.metadata.get("feature", "")
    audit: AuditLogger = ctx.metadata["audit"]

    agent = ArchitectureAgent(ctx.config.get("agents", {}), audit)
    task = AgentTask(
        name="design-architecture",
        input={"feature": feature},
        metadata={"tool": "read_spec"},
    )
    result = agent.run(task)

    if not result.success:
        return StageResult(
            stage_name="architecture",
            status=StageStatus.FAILED,
            error=result.error,
        )
    return StageResult(
        stage_name="architecture",
        status=StageStatus.PASSED,
        output=result.output,
    )


def _stage_backend(ctx: PipelineContext) -> StageResult:
    from examples.agents.backend_agent import BackendAgent

    arch = ctx.stage_outputs.get("architecture")
    if not arch:
        return StageResult(
            stage_name="backend",
            status=StageStatus.FAILED,
            error="Architecture stage output not found in context.",
        )

    audit: AuditLogger = ctx.metadata["audit"]
    agent = BackendAgent(ctx.config.get("agents", {}), audit)
    task = AgentTask(
        name="generate-code",
        input={"architecture": arch},
        metadata={"tool": "write_file"},
    )
    result = agent.run(task)

    if not result.success:
        return StageResult(
            stage_name="backend",
            status=StageStatus.FAILED,
            error=result.error,
        )
    return StageResult(
        stage_name="backend",
        status=StageStatus.PASSED,
        output=result.output,
    )


def _stage_reviewer(ctx: PipelineContext) -> StageResult:
    from examples.agents.reviewer_agent import ReviewerAgent

    backend = ctx.stage_outputs.get("backend")
    if not backend:
        return StageResult(
            stage_name="reviewer",
            status=StageStatus.FAILED,
            error="Backend stage output not found in context.",
        )

    audit: AuditLogger = ctx.metadata["audit"]
    agent = ReviewerAgent(ctx.config.get("agents", {}), audit)
    task = AgentTask(
        name="review-code",
        input={"files": backend["files"]},
        metadata={"tool": "read_file"},
    )
    result = agent.run(task)

    if not result.success:
        return StageResult(
            stage_name="reviewer",
            status=StageStatus.FAILED,
            error=result.error,
        )
    return StageResult(
        stage_name="reviewer",
        status=StageStatus.PASSED,
        output=result.output,
    )


# ---------------------------------------------------------------------------
# Pipeline builder
# ---------------------------------------------------------------------------

def build_example_pipeline(
    feature: str,
    config: dict | None = None,
    audit: AuditLogger | None = None,
) -> tuple[PipelineEngine, PipelineContext]:
    """
    Construct a PipelineEngine with the three example stages registered,
    and a PipelineContext ready to run.

    Returns (engine, context) — call engine.run(context) to execute.
    """
    if config is None:
        config = load_config("config_example.yaml")

    if audit is None:
        audit = AuditLogger(
            config.get("audit", {}).get("log_file", "logs/audit.jsonl")
        )

    # Override pipeline stages so only our three run
    config = {
        **config,
        "pipeline": {
            "stages": ["architecture", "backend", "reviewer"],
            "fail_fast": True,
        },
    }

    engine = PipelineEngine(config, audit)

    # Register the three example stages (override any same-named built-ins)
    engine.register_stage(Stage(
        name="architecture",
        description="Derive architecture plan from feature text",
        handler=_stage_architecture,
        depends_on=[],
    ))
    engine.register_stage(Stage(
        name="backend",
        description="Generate Python source files from architecture plan",
        handler=_stage_backend,
        depends_on=["architecture"],
    ))
    engine.register_stage(Stage(
        name="reviewer",
        description="Run AST static analysis on generated code",
        handler=_stage_reviewer,
        depends_on=["backend"],
    ))

    context = PipelineContext(
        project_name="example",
        config=config,
        workspace=Path("."),
        metadata={"audit": audit, "feature": feature},
    )

    return engine, context
