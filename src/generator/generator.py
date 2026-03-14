"""
ProjectGenerator — creates a complete AI-native project scaffold.

Generated layout:
    <project-name>/
        docs/
            spec.md            ← fill in requirements and architecture
            threat-model.md    ← identify risks before implementation
            tasks.md           ← task list for AI agents
        agents/
            __init__.py
            backend_agent.py   ← stub; implement execute()
            testing_agent.py   ← stub; implement execute()
            security_agent.py  ← stub; implement execute()
        config_example.yaml    ← copy to config.yaml and customize
        .gitignore
        README.md
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from textwrap import dedent


# ── Document templates ─────────────────────────────────────────────────────────

_SPEC = """\
# Specification — {project_name}

## Overview

<!-- What does this system do? One paragraph. -->

## Requirements

<!-- Functional requirements (what the system must do) -->

### Functional
-

### Non-Functional
-

## Architecture

<!-- Describe system components and how they interact. -->

## Acceptance Criteria

<!-- Define measurable "done" conditions for each requirement. -->
-
"""

_THREAT_MODEL = """\
# Threat Model — {project_name}

> Complete this document before writing any implementation code.
> See docs/threat-model.md in AI Development System for guidance.

## Critical Assets

<!-- List sensitive data, credentials, and infrastructure components. -->
-

## Attack Surfaces

<!-- Where can malicious input enter the system? -->
-

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
|      |           |        |            |

## Action Classification

| Action | Level | Gate |
|--------|-------|------|
| (read data)   | 1 — Safe      | none |
| (write data)  | 2 — Sensitive | logged |
| (deploy/delete) | 3 — Critical | human approval |
"""

_TASKS = """\
# Tasks — {project_name}

Generated: {date}

## Backlog

<!-- Add tasks for AI agents. Format: - [ ] <task description> [<agent>] -->

- [ ] Implement core feature X [backend-agent]
- [ ] Write tests for X [testing-agent]
- [ ] Security review of X [security-agent]

## In Progress

-

## Done

-
"""

_AGENT = '''\
"""
{agent_name} — {project_name}

Implement execute() to connect this agent to an LLM or tool.

TODO: Replace NotImplementedError with real logic.
"""

from __future__ import annotations

from typing import Any

from src.agents.base import AgentTask, BaseAgent
from src.agents.registry import register


@register
class {class_name}(BaseAgent):
    name = "{agent_name}"
    allowed_tools = [
        # TODO: list only tools this agent actually needs (least privilege)
        "read_file",
        "write_file",
    ]

    def execute(self, task: AgentTask) -> Any:
        # TODO: implement agent logic
        # Typical pattern:
        #   1. Extract input from task.input
        #   2. Build a prompt or tool call
        #   3. Call LLM API (see config_example.yaml → llm section)
        #   4. Parse and return structured output
        raise NotImplementedError(
            f"{{self.name}}.execute() is not yet implemented."
        )
'''

_GITIGNORE = """\
# Python
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
venv/
env/

# Logs
logs/
*.log
*.jsonl

# Secrets — use config_example.yaml as a template, never commit config.yaml
config.yaml

# IDE
.vscode/settings.json
.idea/
"""

_README = """\
# {project_name}

An AI-native project built on [AI Development System v2](https://github.com/javiermorron/AI-Development-System-v1).

## Getting Started

```bash
pip install -r requirements.txt
```

## Development Flow

```
1. Fill in docs/spec.md          ← define requirements and architecture
2. Complete docs/threat-model.md ← identify risks before writing code
3. Update docs/tasks.md          ← list tasks for each agent
4. Implement agents/             ← each agent does one job
5. Run: aidev pipeline run --config config.yaml
```

## Documentation

- [Specification](docs/spec.md)
- [Threat Model](docs/threat-model.md)
- [Tasks](docs/tasks.md)
"""

_CONFIG = """\
# {project_name} — Configuration
# Copy from AI Development System config_example.yaml and customize.

system:
  name: "{project_name}"
  version: "0.1.0"
  environment: "development"

agents:
  allowed_tools:
    backend-agent:  ["read_file", "write_file", "run_tests"]
    testing-agent:  ["read_file", "write_file", "run_tests"]
    security-agent: ["read_file", "scan_code"]

pipeline:
  stages:
    - specification
    - threat_modeling
    - security_rules
    - implementation
    - testing
    - code_review
    - security_review
    - policy_validation
  fail_fast: true

audit:
  log_file: "logs/audit.jsonl"
  include_inputs: true
  include_outputs: true
"""


# ── Generator ──────────────────────────────────────────────────────────────────

class ProjectGenerator:
    """Generates a new AI-native project scaffold from templates."""

    def generate(self, project_name: str, output_dir: Path) -> None:
        root = output_dir / project_name
        root.mkdir(parents=True, exist_ok=True)

        self._write_docs(root, project_name)
        self._write_agents(root, project_name)
        self._write_root_files(root, project_name)

    # ------------------------------------------------------------------

    def _write_docs(self, root: Path, project_name: str) -> None:
        docs = root / "docs"
        docs.mkdir(exist_ok=True)

        (docs / "spec.md").write_text(
            _SPEC.format(project_name=project_name), encoding="utf-8"
        )
        (docs / "threat-model.md").write_text(
            _THREAT_MODEL.format(project_name=project_name), encoding="utf-8"
        )
        (docs / "tasks.md").write_text(
            _TASKS.format(project_name=project_name, date=date.today().isoformat()),
            encoding="utf-8",
        )

    def _write_agents(self, root: Path, project_name: str) -> None:
        agents_dir = root / "agents"
        agents_dir.mkdir(exist_ok=True)
        (agents_dir / "__init__.py").write_text("", encoding="utf-8")

        for filename, class_name, agent_name in [
            ("backend_agent",  "BackendAgent",  "backend-agent"),
            ("testing_agent",  "TestingAgent",  "testing-agent"),
            ("security_agent", "SecurityAgent", "security-agent"),
        ]:
            content = _AGENT.format(
                agent_name=agent_name,
                class_name=class_name,
                project_name=project_name,
            )
            (agents_dir / f"{filename}.py").write_text(content, encoding="utf-8")

    def _write_root_files(self, root: Path, project_name: str) -> None:
        (root / ".gitignore").write_text(_GITIGNORE, encoding="utf-8")
        (root / "README.md").write_text(
            _README.format(project_name=project_name), encoding="utf-8"
        )
        (root / "config_example.yaml").write_text(
            _CONFIG.format(project_name=project_name), encoding="utf-8"
        )
