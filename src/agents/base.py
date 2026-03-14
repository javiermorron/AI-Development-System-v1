"""
BaseAgent — abstract base class for all AI development agents.

Every agent in the system extends BaseAgent and implements execute().
The base class enforces the security + audit contract automatically:
    1. Validate input before execution
    2. Check tool authorization
    3. Classify action level (Safe / Sensitive / Critical)
    4. Emit audit log entry on success or failure
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..audit.logger import AuditLogger
from ..security.classifier import ActionClassifier
from ..security.validator import InputValidator


@dataclass
class AgentTask:
    """A unit of work dispatched to an agent."""

    name: str
    input: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResult:
    """The outcome of an agent executing a task."""

    success: bool
    output: Any
    agent_name: str
    task_name: str
    error: str | None = None


class BaseAgent(ABC):
    """
    Abstract base for all agents.

    Subclass contract:
        - Set `name` (str) as a class attribute — used as the agent identifier.
        - Set `allowed_tools` (list[str]) listing permitted tool names.
        - Implement `execute(task: AgentTask) -> Any`.
    """

    name: str = "base-agent"
    allowed_tools: list[str] = []

    def __init__(self, config: dict, audit_logger: AuditLogger) -> None:
        self.config = config
        self.audit = audit_logger
        self._classifier = ActionClassifier()
        self._validator = InputValidator()

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, task: AgentTask) -> AgentResult:
        """
        Execute a task with full security validation and audit logging.
        Call this instead of execute() directly.
        """
        # 1. Validate input
        validation = self._validator.validate(task.input)
        if not validation.is_valid:
            self._emit_audit(task, success=False, output={"errors": validation.errors})
            return AgentResult(
                success=False,
                output=None,
                agent_name=self.name,
                task_name=task.name,
                error=f"Input validation failed: {validation.errors}",
            )

        # 2. Check tool authorization
        requested_tool = task.metadata.get("tool")
        if requested_tool and requested_tool not in self.allowed_tools:
            error = (
                f"Agent '{self.name}' is not authorized to use tool '{requested_tool}'. "
                f"Allowed: {self.allowed_tools}"
            )
            self._emit_audit(task, success=False, output={"error": error})
            return AgentResult(
                success=False,
                output=None,
                agent_name=self.name,
                task_name=task.name,
                error=error,
            )

        # 3. Execute
        try:
            output = self.execute(task)
            self._emit_audit(task, success=True, output=output)
            return AgentResult(
                success=True,
                output=output,
                agent_name=self.name,
                task_name=task.name,
            )
        except NotImplementedError:
            error = f"Agent '{self.name}' has not implemented execute() yet."
            self._emit_audit(task, success=False, output={"error": error})
            return AgentResult(
                success=False,
                output=None,
                agent_name=self.name,
                task_name=task.name,
                error=error,
            )
        except Exception as exc:
            self._emit_audit(task, success=False, output={"error": str(exc)})
            return AgentResult(
                success=False,
                output=None,
                agent_name=self.name,
                task_name=task.name,
                error=str(exc),
            )

    # ------------------------------------------------------------------
    # To implement in subclasses
    # ------------------------------------------------------------------

    @abstractmethod
    def execute(self, task: AgentTask) -> Any:
        """
        Agent-specific logic. Receives a validated AgentTask, returns any output.

        TODO (per agent): call LLM API, run tools, return structured result.
        """
        ...

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit_audit(self, task: AgentTask, success: bool, output: Any) -> None:
        self.audit.log_action(
            agent=self.name,
            tool=task.metadata.get("tool", task.name),
            input_data=task.input,
            output=output,
            success=success,
            metadata=task.metadata if task.metadata else None,
        )
