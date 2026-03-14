# Architecture

This document describes the technical architecture of the AI Development System.

## Overview

The system is organized in four layers:

```
Developer / CLI
      |
      v
Pipeline Engine  <-->  Security Layer  +  Audit Logger
      |
      v
  Agents (Architecture -> Backend -> Reviewer)
      |
      v
generated/<project-slug>/
```

Each layer has a single, narrow responsibility.

---

## Layer 0 — Developer interface

The entry point is either:

- `aidev` CLI (`src/cli.py`) — Click command groups for all subsystems
- `python -m examples.run_pipeline` — direct runner for the 3-agent example

Config is loaded from `config_example.yaml` via `src/config.py`. The config file controls which pipeline stages run, per-agent tool allowlists, audit log path, and security settings.

---

## Layer 1 — Pipeline Engine

**File:** `src/pipeline/engine.py`

`PipelineEngine` owns:

- An ordered list of `Stage` objects (name, handler function, dependencies)
- A `run(context: PipelineContext) -> list[StageResult]` method
- Fail-fast: if any stage returns `StageStatus.FAILED`, execution stops immediately
- Dependency checking: stages only run after all declared dependencies have passed

`PipelineContext` is a dataclass with a single important field:

```python
stage_outputs: dict[str, Any]  # keyed by stage name
```

This is the **only** data channel between stages. No globals, no side-channels.

---

## Layer 1a — Security Layer (cross-cutting)

**Files:** `src/security/`

Every user input and agent action passes through three independent checks:

| Component | What it does |
|-----------|-------------|
| `ActionClassifier` | Classifies action as L1 (Safe), L2 (Sensitive), or L3 (Critical) using keyword matching |
| `InputValidator` | Checks input length, null bytes, and structural depth |
| `PromptSanitizer` | Runs 9 regex patterns for prompt injection, jailbreak attempts, instruction overrides |

L3 (Critical) actions pause pipeline execution and call `_request_human_approval()` in the orchestrator.

---

## Layer 1b — Audit Logger (cross-cutting)

**File:** `src/audit/logger.py`

`AuditLogger` writes append-only JSON Lines to `audit.jsonl` (path configurable). Every logged entry contains:

```json
{
  "timestamp": "2026-03-14T12:00:00Z",
  "agent": "backend-agent",
  "tool": "write_file",
  "input": "...",
  "output": "...",
  "level": 2
}
```

The log is never modified, only appended. `read_log()` returns parsed entries for `aidev audit show`.

---

## Layer 2 — Agents

### BaseAgent

**File:** `src/agents/base.py`

Abstract base class enforcing a four-step execution contract:

1. Validate input via `InputValidator`
2. Check tool authorization against `allowed_tools`
3. Call `execute()` (abstract, implemented by subclass)
4. Log result via `AuditLogger`

Subclasses only implement `execute(task: AgentTask) -> AgentResult`.

### Agent Registry

**File:** `src/agents/registry.py`

Agents register via `@register("name")` decorator at module import time. `get_agent(name)` returns the class. `list_agents()` returns all registered names.

### ArchitectureAgent

**File:** `examples/agents/architecture_agent.py`

Input: plain-text feature description
Output: `stage_outputs["architecture"]` containing:

```python
{
    "entities": ["User", "Token"],
    "components": ["auth", "jwt"],
    "routes": [{"method": "POST", "path": "/users", "handler": "create_user", "security_level": 2}, ...],
    "security_concerns": ["JWT secret must not be hardcoded", ...]
}
```

Implementation: keyword map with 27+ entity types, security keyword detection, route derivation (5 CRUD routes per entity).

### BackendAgent

**File:** `examples/agents/backend_agent.py`

Input: `stage_outputs["architecture"]`
Output: `stage_outputs["backend"]` containing:

```python
{
    "files": {"main.py": "...", "models.py": "...", ...},
    "entities_implemented": ["User", "Token"],
    "route_count": 10,
    "lines_of_code": 420
}
```

Writes files to `context.workspace / filename`. Generates 9+ files using Python string templates — no LLM required:

- `main.py` — FastAPI app with all routers mounted
- `models.py` — Pydantic BaseModel per entity with typed fields
- `schemas.py` — Create/Update/Response schema variants
- `services.py` — Business logic calling repository layer
- `repositories.py` — In-memory dict-based CRUD store
- `routers/<entity>.py` — APIRouter with 5 endpoints, HTTPException handling
- `routers/__init__.py` — Router aggregation
- `requirements.txt` — fastapi, uvicorn, pydantic
- `README.md` — Setup and run instructions

### ReviewerAgent

**File:** `examples/agents/reviewer_agent.py`

Input: files written to disk by BackendAgent
Output: `stage_outputs["reviewer"]` containing:

```python
{
    "approved": True,
    "score": 9.5,
    "summary": "...",
    "findings": [{"severity": "WARNING", "file": "main.py", "line": 12, "message": "..."}],
    "metrics": {"files_reviewed": 7, "docstring_coverage": "85%", ...}
}
```

Uses `ast.parse()` for real static analysis. Checks:

- Missing docstrings on classes and functions
- Missing return type annotations
- Unannotated parameters
- `NotImplementedError` stubs
- Hardcoded credential patterns
- Debug `print()` statements
- TODO/FIXME comments

Score formula: `10.0 - errors*2.0 - warnings*0.5` (clamped to 0-10).

---

## Layer 3 — Generated Output

Each pipeline run produces a complete, runnable FastAPI project at:

```
generated/<slugified-feature-name>/
```

The slug is computed by `src/utils.slugify()`: lowercase, strip punctuation, spaces to hyphens, deduplicate hyphens, truncate to 40 chars.

The generated project has zero external dependencies beyond the Python packages listed in its own `requirements.txt`.

---

## Data flow summary

```
feature text
    |
    v
ArchitectureAgent.execute()
    |  writes stage_outputs["architecture"]
    v
BackendAgent.execute()
    |  reads stage_outputs["architecture"]
    |  writes files to generated/<slug>/
    |  writes stage_outputs["backend"]
    v
ReviewerAgent.execute()
    |  reads stage_outputs["backend"]["files"]
    |  parses files with ast.parse()
    |  writes stage_outputs["reviewer"]
    v
Pipeline complete
```

---

## Configuration

`config_example.yaml` controls runtime behavior:

```yaml
pipeline:
  stages: [architecture, backend, reviewer]

agents:
  architecture-agent:
    allowed_tools: [read_file, analyze_code]
  backend-agent:
    allowed_tools: [write_file, read_file]
  reviewer-agent:
    allowed_tools: [read_file, analyze_code, run_tests]

security:
  level: strict
  require_human_approval_for_level3: true

audit:
  log_path: audit.jsonl
```
