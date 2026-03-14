# Skill: documentation

**Type:** MCP Skill (concept)
**Status:** Planned for v3

---

## Purpose

Automatically generate or update `docs/` Markdown files after a pipeline run. Keeps documentation in sync with the actual generated code without manual effort.

---

## Trigger

Activates after `ReviewerAgent` completes. Can also be triggered manually via CLI:

```bash
aidev skill run documentation --project generated/my-feature/
```

---

## Inputs

```python
{
    "project_path": Path,           # generated/<slug>/
    "feature_description": str,     # original feature text
    "stage_outputs": {
        "architecture": {...},
        "backend": {...},
        "reviewer": {...}
    }
}
```

---

## Outputs

Writes or updates files in the generated project's docs folder:

| File | Content |
|------|---------|
| `docs/api-reference.md` | All routes, request/response schemas, example curl commands |
| `docs/data-model.md` | Entity descriptions, field types, relationships |
| `docs/security.md` | Security concerns flagged by ArchitectureAgent |
| `docs/reviewer-report.md` | ReviewerAgent score, findings, and metrics |

---

## Implementation approach (v3)

```python
@register("documentation-skill")
class DocumentationSkill(BaseAgent):
    name = "documentation-skill"
    allowed_tools = ["write_file", "read_file"]

    def execute(self, task: AgentTask) -> AgentResult:
        arch = task.metadata["stage_outputs"]["architecture"]
        reviewer = task.metadata["stage_outputs"]["reviewer"]
        workspace = task.metadata["workspace"]

        docs_dir = workspace / "docs"
        docs_dir.mkdir(exist_ok=True)

        files_written = []

        api_ref = self._render_api_reference(arch["routes"], arch["entities"])
        (docs_dir / "api-reference.md").write_text(api_ref, encoding="utf-8")
        files_written.append("docs/api-reference.md")

        report = self._render_reviewer_report(reviewer)
        (docs_dir / "reviewer-report.md").write_text(report, encoding="utf-8")
        files_written.append("docs/reviewer-report.md")

        return AgentResult(success=True, output={"files_written": files_written})
```

---

## Example: generated api-reference.md

```markdown
# API Reference

## Users

### POST /api/v1/users
Create a new user.

**Request body:**
| Field | Type | Required |
|-------|------|----------|
| name  | str  | yes      |
| email | str  | yes      |

**Response:** `201 Created` — UserResponse

**curl:**
    curl -X POST http://localhost:8000/api/v1/users \
      -H "Content-Type: application/json" \
      -d '{"name": "Alice", "email": "alice@example.com"}'
```

---

## Security classification

| Action | Level |
|--------|-------|
| Read stage_outputs | L1 (Safe) |
| Read generated Python files | L1 (Safe) |
| Write Markdown to docs/ | L2 (Sensitive) |

---

## LLM upgrade path (v4)

In v4 this skill can be upgraded to call the Claude API to write richer prose documentation — usage examples, error handling guides, authentication walkthroughs. The interface stays identical; only `_render_api_reference()` gets a real LLM call instead of a template.

```python
# v4 upgrade — drop-in replacement for _render_api_reference()
def _render_api_reference(self, routes, entities) -> str:
    import anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{
            "role": "user",
            "content": f"Write a complete API reference for these routes: {routes}"
        }]
    )
    return response.content[0].text
```
