"""
Stage data types for the pipeline engine.

A Stage wraps a handler callable that receives a PipelineContext and
returns a StageResult. Stages may declare dependencies on other stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Callable, Any

if TYPE_CHECKING:
    from .engine import PipelineContext


class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED  = "passed"
    FAILED  = "failed"
    SKIPPED = "skipped"


@dataclass
class StageResult:
    stage_name: str
    status: StageStatus
    output: Any = None
    error: str | None = None


@dataclass
class Stage:
    name: str
    description: str
    handler: Callable[["PipelineContext"], StageResult]
    required: bool = True
    depends_on: list[str] = field(default_factory=list)
