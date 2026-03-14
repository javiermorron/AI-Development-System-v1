"""
Input validator — checks external inputs before they reach agents.

Validates prompts, webhook payloads, file contents, and any dict-structured
inputs passed across trust boundaries. Extend _check_* methods to add rules.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DEFAULT_MAX_LENGTH = 10_000


@dataclass
class ValidationResult:
    is_valid: bool
    errors: list[str] = field(default_factory=list)


class InputValidator:
    """Validates external inputs for length, null bytes, and nested content."""

    def validate(
        self, data: Any, max_length: int = DEFAULT_MAX_LENGTH
    ) -> ValidationResult:
        errors: list[str] = []

        if data is None:
            return ValidationResult(is_valid=False, errors=["Input cannot be None"])

        if isinstance(data, str):
            errors.extend(self._check_string(data, max_length))

        elif isinstance(data, dict):
            for key, value in data.items():
                nested = self.validate(value, max_length)
                if not nested.is_valid:
                    errors.extend(f"{key}: {e}" for e in nested.errors)

        elif isinstance(data, list):
            for i, item in enumerate(data):
                nested = self.validate(item, max_length)
                if not nested.is_valid:
                    errors.extend(f"[{i}]: {e}" for e in nested.errors)

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    # ------------------------------------------------------------------
    # Internal checks (extend to add more rules)
    # ------------------------------------------------------------------

    def _check_string(self, text: str, max_length: int) -> list[str]:
        errors: list[str] = []
        if len(text) > max_length:
            errors.append(
                f"Input length {len(text)} exceeds maximum {max_length} characters"
            )
        if "\x00" in text:
            errors.append("Input contains null bytes")
        return errors
