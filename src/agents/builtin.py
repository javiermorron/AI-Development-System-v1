"""
Built-in agent stubs for the five core roles defined in docs/architecture.md.

Each agent is registered automatically when this module is imported.
Implement execute() in each class to connect real LLM / tool logic.

TODO (v3): Replace stub execute() methods with actual LLM API calls.
"""

from __future__ import annotations

from typing import Any

from .base import AgentTask, BaseAgent
from .registry import register


@register
class BackendAgent(BaseAgent):
    """
    Implements core backend features based on specs in docs/.
    TODO: Read docs/spec.md, call LLM, write output to feature branch.
    """

    name = "backend-agent"
    allowed_tools = ["read_file", "write_file", "run_tests", "run_command"]

    def execute(self, task: AgentTask) -> Any:
        # TODO: Parse task.input["spec"] → call LLM → return generated code
        raise NotImplementedError(
            "BackendAgent.execute() is not yet implemented. "
            "Connect an LLM API and implement code generation logic here."
        )


@register
class TestingAgent(BaseAgent):
    """
    Generates and runs tests for implemented features.
    TODO: Inspect feature code, generate pytest tests, run and report results.
    """

    name = "testing-agent"
    allowed_tools = ["read_file", "write_file", "run_tests"]

    def execute(self, task: AgentTask) -> Any:
        # TODO: Receive code path from task.input["target"], generate tests
        raise NotImplementedError(
            "TestingAgent.execute() is not yet implemented. "
            "Implement test generation and pytest execution here."
        )


@register
class SecurityAgent(BaseAgent):
    """
    Reviews code for vulnerabilities, checks against docs/security-rules.md.
    TODO: Integrate bandit / semgrep or LLM-based review.
    """

    name = "security-agent"
    allowed_tools = ["read_file", "scan_code", "check_dependencies"]

    def execute(self, task: AgentTask) -> Any:
        # TODO: Run bandit/semgrep on task.input["target_path"]
        raise NotImplementedError(
            "SecurityAgent.execute() is not yet implemented. "
            "Integrate a security scanner (bandit, semgrep) or LLM review here."
        )


@register
class DocsAgent(BaseAgent):
    """
    Keeps documentation in docs/ synchronized with code changes.
    TODO: Diff changed files, update relevant docs, commit to docs branch.
    """

    name = "docs-agent"
    allowed_tools = ["read_file", "write_file"]

    def execute(self, task: AgentTask) -> Any:
        # TODO: Read changed file list from task.input["changed_files"], update docs
        raise NotImplementedError(
            "DocsAgent.execute() is not yet implemented. "
            "Implement documentation sync logic here."
        )


@register
class ReleaseAgent(BaseAgent):
    """
    Automates versioning, changelog generation, and release tagging.
    TODO: Integrate Release Please or equivalent tooling.
    """

    name = "release-agent"
    allowed_tools = ["read_file", "tag_release", "generate_notes"]

    def execute(self, task: AgentTask) -> Any:
        # TODO: Parse task.input["version"] and task.input["commits"], generate release
        raise NotImplementedError(
            "ReleaseAgent.execute() is not yet implemented. "
            "Implement version bump and release note generation here."
        )
