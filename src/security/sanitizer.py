"""
Prompt sanitizer — detects and removes prompt injection patterns.

Prompts received from external sources (user input, webhooks, external APIs)
must be sanitized before forwarding to an LLM. Injection patterns that try to
override system instructions are replaced with [REDACTED].
"""

from __future__ import annotations

import re

# Patterns that are characteristic of prompt injection attempts.
# Based on common jailbreak / override techniques.
_INJECTION_PATTERNS: list[str] = [
    r"ignore\s+(all\s+)?previous\s+instructions?",
    r"forget\s+(everything|all|your\s+instructions?)",
    r"you\s+are\s+now\s+(?!an?\s+AI)",
    r"act\s+as\s+(?:if\s+you\s+(?:are|were)\s+)?(?:a\s+)?(?!assistant|helpful)",
    r"pretend\s+(you\s+are|to\s+be)",
    r"disregard\s+(your|all|previous)",
    r"new\s+system\s+instructions?:",
    r"<\s*system\s*>",
    r"\[INST\]",
    r"###\s*System\s*:",
]

_COMPILED = [re.compile(p, re.IGNORECASE | re.DOTALL) for p in _INJECTION_PATTERNS]


class PromptSanitizer:
    """Detects and removes prompt injection patterns from text."""

    def sanitize(self, prompt: str) -> str:
        """Return a copy of prompt with injection patterns replaced by [REDACTED]."""
        result = prompt
        for pattern in _COMPILED:
            result = pattern.sub("[REDACTED]", result)
        return result

    def is_safe(self, prompt: str) -> bool:
        """Return True if no injection patterns are detected."""
        return not any(p.search(prompt) for p in _COMPILED)

    def detected_patterns(self, prompt: str) -> list[str]:
        """Return the regex patterns that matched, for logging/alerting."""
        return [p.pattern for p in _COMPILED if p.search(prompt)]
