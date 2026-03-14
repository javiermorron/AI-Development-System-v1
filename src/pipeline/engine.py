"""
PipelineEngine — runs the AI development pipeline stage by stage.

The eight built-in stages map to the pipeline defined in docs/architecture.md.
Each stage has a stub handler that passes immediately; replace handlers with
real integrations as the system evolves toward v3/v4.

Custom stages can be registered with engine.register_stage(Stage(...)).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .stages import Stage, StageResult, StageStatus
from ..audit.logger import AuditLogger


# Default ordered stage list (matches config_example.yaml)
BUILTIN_STAGE_NAMES = [
    "specification",
    "threat_modeling",
    "security_rules",
    "implementation",
    "testing",
    "code_review",
    "security_review",
    "policy_validation",
]

_STAGE_DESCRIPTIONS = {
    "specification":    "Validate that required spec documents exist in docs/",
    "threat_modeling":  "Ensure threat model is up to date for this feature",
    "security_rules":   "Confirm security rules are defined and current",
    "implementation":   "Dispatch implementation tasks to AI agents",
    "testing":          "Run automated test suite and check coverage",
    "code_review":      "AI-assisted code review (architecture, logic, best practices)",
    "security_review":  "Automated security scan (injection, secrets, dependencies)",
    "policy_validation":"Verify compliance with docs/security-rules.md",
}


@dataclass
class PipelineContext:
    """
    Shared mutable context passed to every stage handler.
    Stages read config and write their outputs here for downstream stages.
    """

    project_name: str
    config: dict
    workspace: Path
    stage_outputs: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


class PipelineEngine:
    """Executes a sequence of pipeline stages with audit logging."""

    def __init__(self, config: dict, audit_logger: AuditLogger) -> None:
        self.config = config
        self.audit = audit_logger
        self._stages: dict[str, Stage] = {}
        self._register_builtin_stages()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_stage(self, stage: Stage) -> None:
        """Register a custom stage (or override a built-in stage handler)."""
        self._stages[stage.name] = stage

    def run(self, context: PipelineContext) -> list[StageResult]:
        """
        Run all configured stages in order.
        Returns a list of StageResult objects, one per stage attempted.
        """
        enabled: list[str] = (
            context.config.get("pipeline", {}).get("stages", BUILTIN_STAGE_NAMES)
        )
        fail_fast: bool = context.config.get("pipeline", {}).get("fail_fast", True)

        results: list[StageResult] = []
        completed: set[str] = set()

        for stage_name in enabled:
            stage = self._stages.get(stage_name)

            if stage is None:
                results.append(StageResult(
                    stage_name=stage_name,
                    status=StageStatus.SKIPPED,
                    error=f"Stage '{stage_name}' is not registered.",
                ))
                continue

            # Dependency check
            if stage.depends_on:
                missing = [d for d in stage.depends_on if d not in completed]
                if missing:
                    results.append(StageResult(
                        stage_name=stage_name,
                        status=StageStatus.SKIPPED,
                        error=f"Unmet dependencies: {missing}",
                    ))
                    if fail_fast and stage.required:
                        break
                    continue

            result = self._run_stage(stage, context)
            results.append(result)

            if result.status == StageStatus.PASSED:
                completed.add(stage_name)
                context.stage_outputs[stage_name] = result.output
            elif result.status == StageStatus.FAILED and fail_fast and stage.required:
                break

        return results

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run_stage(self, stage: Stage, context: PipelineContext) -> StageResult:
        self.audit.log_action(
            agent="pipeline-engine",
            tool=stage.name,
            input_data={"project": context.project_name, "stage": stage.name},
            output=None,
            success=True,
            metadata={"description": stage.description},
        )
        try:
            return stage.handler(context)
        except Exception as exc:
            return StageResult(
                stage_name=stage.name,
                status=StageStatus.FAILED,
                error=str(exc),
            )

    def _register_builtin_stages(self) -> None:
        for name in BUILTIN_STAGE_NAMES:
            desc = _STAGE_DESCRIPTIONS.get(name, name)

            def make_handler(stage_name: str):
                def handler(ctx: PipelineContext) -> StageResult:
                    return _stub_handler(stage_name, ctx)
                return handler

            self.register_stage(Stage(
                name=name,
                description=desc,
                handler=make_handler(name),
            ))


# ------------------------------------------------------------------
# Stub handler (replace per stage with real integrations)
# ------------------------------------------------------------------

def _stub_handler(stage_name: str, context: PipelineContext) -> StageResult:
    """
    Passes immediately. Replace with real logic per stage:

        specification    → check docs/ for required files (spec.md, threat-model.md, tasks.md)
        threat_modeling  → diff threat model against code changes; flag new attack surfaces
        security_rules   → parse docs/security-rules.md; verify each rule has a control
        implementation   → call AgentOrchestrator with backend-agent / frontend-agent tasks
        testing          → subprocess: pytest --cov; fail if coverage < threshold
        code_review      → call LLM with diff; return structured review findings
        security_review  → run bandit / semgrep; parse output; fail on HIGH findings
        policy_validation→ re-read docs/security-rules.md; assert each rule is satisfied

    TODO (v3): Implement each handler above.
    """
    return StageResult(
        stage_name=stage_name,
        status=StageStatus.PASSED,
        output={"message": f"Stage '{stage_name}' passed (stub — implement in v3)"},
    )
