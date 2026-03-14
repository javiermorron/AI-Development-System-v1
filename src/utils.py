"""Shared utility helpers for AI Development System."""

from __future__ import annotations

import re


def slugify(text: str, max_length: int = 40) -> str:
    """
    Convert any string into a filesystem-safe directory name.

    Examples:
        "User authentication with JWT tokens" -> "user-authentication-with-jwt-tokens"
        "Order management & payments!"        -> "order-management-payments"
        "  Spaces   and___underscores  "      -> "spaces-and-underscores"
    """
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)       # drop punctuation except hyphens
    text = re.sub(r"[\s_]+", "-", text)         # spaces / underscores → hyphens
    text = re.sub(r"-+", "-", text)             # collapse consecutive hyphens
    text = text.strip("-")
    return text[:max_length].rstrip("-")
