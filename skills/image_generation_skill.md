# Skill: image_generation

**Type:** MCP Skill (concept)
**Status:** Planned for v3

---

## Purpose

Automatically generate SVG architecture diagrams from pipeline execution data. When a pipeline run completes, this skill would produce visual documentation in `assets/images/` without manual authoring.

---

## Trigger

This skill activates after `ReviewerAgent` completes successfully and `context.stage_outputs["reviewer"]["approved"] == True`.

---

## Inputs

Read from `PipelineContext.stage_outputs`:

```python
{
    "architecture": {
        "entities": [...],
        "routes": [...],
        "components": [...]
    },
    "backend": {
        "files": {...},
        "route_count": int
    },
    "reviewer": {
        "score": float,
        "approved": bool
    }
}
```

---

## Outputs

Writes to `assets/images/<project-slug>/`:

| File | Content |
|------|---------|
| `pipeline-flow.svg` | Horizontal stage diagram with entity labels |
| `entity-model.svg` | Entity relationship diagram derived from models.py |
| `route-map.svg` | HTTP method + path table rendered as a visual grid |

---

## Implementation approach (v3)

```python
@register("image-generation-skill")
class ImageGenerationSkill(BaseAgent):
    name = "image-generation-skill"
    allowed_tools = ["write_file"]

    def execute(self, task: AgentTask) -> AgentResult:
        arch = task.metadata["stage_outputs"]["architecture"]
        entities = arch["entities"]
        routes = arch["routes"]

        svg = self._render_pipeline_svg(entities, routes)
        output_path = task.metadata["workspace"] / "pipeline-flow.svg"
        output_path.write_text(svg, encoding="utf-8")

        return AgentResult(success=True, output={"files_written": ["pipeline-flow.svg"]})

    def _render_pipeline_svg(self, entities: list, routes: list) -> str:
        # Build SVG string from entity/route data
        ...
```

---

## Security classification

| Action | Level |
|--------|-------|
| Read stage_outputs | L1 (Safe) |
| Write SVG files to assets/ | L2 (Sensitive) |

No L3 actions — this skill never modifies production resources.

---

## Integration point

Register in `examples/pipeline.py` as an optional post-pipeline stage:

```python
engine.register_stage(
    "image-generation",
    _stage_image_generation,
    depends_on=["reviewer"],
    optional=True  # pipeline still passes if this fails
)
```
