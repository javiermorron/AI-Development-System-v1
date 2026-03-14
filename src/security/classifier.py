"""
Action classifier — maps any system action to its security level.

Levels are defined in docs/threat-model.md:
    Level 1 (SAFE)      — read / analyze — no gate
    Level 2 (SENSITIVE) — data modification — logged, proceeds automatically
    Level 3 (CRITICAL)  — deploy / delete / financial — human approval required
"""

from __future__ import annotations

from enum import Enum


class ActionLevel(Enum):
    SAFE = 1
    SENSITIVE = 2
    CRITICAL = 3


# Keywords that indicate a critical (Level 3) action
_CRITICAL_KEYWORDS = frozenset({
    "deploy", "delete", "drop", "destroy", "remove", "purge", "truncate",
    "change_permissions", "revoke", "financial", "payment", "transfer",
    "migrate", "rollback", "production", "overwrite", "format",
})

# Keywords that indicate a sensitive (Level 2) action
_SENSITIVE_KEYWORDS = frozenset({
    "create", "update", "insert", "write", "save", "send",
    "post", "put", "patch", "modify", "push", "commit", "merge",
})


class ActionClassifier:
    """Classifies agent actions into security levels (1 / 2 / 3)."""

    def classify(self, action: str) -> ActionLevel:
        normalized = action.lower().replace("-", "_").replace(" ", "_")
        if any(kw in normalized for kw in _CRITICAL_KEYWORDS):
            return ActionLevel.CRITICAL
        if any(kw in normalized for kw in _SENSITIVE_KEYWORDS):
            return ActionLevel.SENSITIVE
        return ActionLevel.SAFE

    def requires_human_approval(self, action: str) -> bool:
        return self.classify(action) == ActionLevel.CRITICAL

    def describe(self, action: str) -> str:
        level = self.classify(action)
        return {
            ActionLevel.SAFE:      "Level 1 — Safe: read/analyze, no gate required",
            ActionLevel.SENSITIVE: "Level 2 — Sensitive: data modification, logged",
            ActionLevel.CRITICAL:  "Level 3 — Critical: requires human approval",
        }[level]
