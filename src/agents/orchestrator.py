"""
AgentOrchestrator — coordinates multiple agents to execute a development plan.

Responsibilities:
    - Instantiate agents on demand (cached per session)
    - Enforce human-in-the-loop for Level 3 / Critical actions
    - Respect fail_fast config for sequential plans
    - Delegate security classification to ActionClassifier
"""

from __future__ import annotations

from dataclasses import dataclass

from .base import AgentResult, AgentTask, BaseAgent
from .registry import get_agent, list_agents
from ..audit.logger import AuditLogger
from ..security.classifier import ActionClassifier, ActionLevel


@dataclass
class OrchestrationPlan:
    """An ordered list of (agent_name, task) pairs to execute sequentially."""

    tasks: list[tuple[str, AgentTask]]


class AgentOrchestrator:
    """Runs an OrchestrationPlan, enforcing security gates between steps."""

    def __init__(self, config: dict, audit_logger: AuditLogger) -> None:
        self.config = config
        self.audit = audit_logger
        self._classifier = ActionClassifier()
        self._agent_instances: dict[str, BaseAgent] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_plan(self, plan: OrchestrationPlan) -> list[AgentResult]:
        """
        Execute all tasks in the plan in order.
        Stops early on failure if pipeline.fail_fast is True (default).
        """
        fail_fast: bool = self.config.get("pipeline", {}).get("fail_fast", True)
        results: list[AgentResult] = []

        for agent_name, task in plan.tasks:
            agent = self._get_or_create(agent_name)

            if agent is None:
                result = AgentResult(
                    success=False,
                    output=None,
                    agent_name=agent_name,
                    task_name=task.name,
                    error=f"Agent '{agent_name}' is not registered. "
                          f"Available: {list_agents()}",
                )
                results.append(result)
                if fail_fast:
                    break
                continue

            # Security gate for critical actions
            action = task.metadata.get("action", task.name)
            if self._classifier.classify(action) == ActionLevel.CRITICAL:
                if not self._request_human_approval(agent_name, task):
                    result = AgentResult(
                        success=False,
                        output=None,
                        agent_name=agent_name,
                        task_name=task.name,
                        error="Critical action was not approved by human reviewer.",
                    )
                    self.audit.log_action(
                        agent=agent_name,
                        tool=action,
                        input_data=task.input,
                        output={"status": "rejected_by_human"},
                        success=False,
                    )
                    results.append(result)
                    if fail_fast:
                        break
                    continue

            result = agent.run(task)
            results.append(result)

            if not result.success and fail_fast:
                break

        return results

    def available_agents(self) -> list[str]:
        return list_agents()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_or_create(self, name: str) -> BaseAgent | None:
        if name not in self._agent_instances:
            agent_cls = get_agent(name)
            if agent_cls is None:
                return None
            agent_config = self.config.get("agents", {})
            self._agent_instances[name] = agent_cls(agent_config, self.audit)
        return self._agent_instances[name]

    def _request_human_approval(self, agent_name: str, task: AgentTask) -> bool:
        """Blocking prompt for human-in-the-loop approval of critical actions."""
        print(
            f"\n[CRITICAL ACTION GATE]\n"
            f"  Agent : {agent_name}\n"
            f"  Task  : {task.name}\n"
            f"  Input : {task.input}\n"
        )
        try:
            answer = input("  Approve this action? (yes / no): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            answer = "no"
        return answer in ("yes", "y")
