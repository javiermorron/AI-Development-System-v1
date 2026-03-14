"""
Audit logger — append-only JSON Lines log of every agent action.

Each entry records: agent, tool, input, output, success, timestamp.
This log is the primary traceability and audit trail for the system.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class AuditLogger:
    """
    Writes one JSON object per line to an append-only log file.

    Log format (per entry):
        {
            "timestamp": "<ISO-8601 UTC>",
            "agent":     "<agent-name>",
            "tool":      "<tool-or-stage-name>",
            "success":   true | false,
            "input":     <any>,   # omitted if include_inputs=False
            "output":    <any>,   # omitted if include_outputs=False
            "metadata":  <dict>   # optional, caller-supplied
        }
    """

    def __init__(
        self,
        log_file: str | Path,
        include_inputs: bool = True,
        include_outputs: bool = True,
    ) -> None:
        self.log_file = Path(log_file)
        self.include_inputs = include_inputs
        self.include_outputs = include_outputs

        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        self._logger = logging.getLogger(f"audit.{id(self)}")
        self._logger.propagate = False
        if not self._logger.handlers:
            handler = logging.FileHandler(self.log_file, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_action(
        self,
        *,
        agent: str,
        tool: str,
        input_data: Any,
        output: Any,
        success: bool,
        metadata: dict | None = None,
    ) -> None:
        """Append one audit entry to the log file."""
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent": agent,
            "tool": tool,
            "success": success,
        }
        if self.include_inputs:
            entry["input"] = self._safe_serialize(input_data)
        if self.include_outputs and output is not None:
            entry["output"] = self._safe_serialize(output)
        if metadata:
            entry["metadata"] = metadata

        self._logger.info(json.dumps(entry, ensure_ascii=False))

    def read_log(self) -> list[dict]:
        """Return all log entries as a list of dicts."""
        if not self.log_file.exists():
            return []
        entries: list[dict] = []
        with self.log_file.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return entries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _safe_serialize(self, obj: Any) -> Any:
        """Return obj if JSON-serializable, otherwise its string representation."""
        try:
            json.dumps(obj)
            return obj
        except (TypeError, ValueError):
            return str(obj)
