"""Configuration loader for AI Development System."""

from __future__ import annotations

from pathlib import Path

import yaml


def load_config(path: str | Path) -> dict:
    """Load a YAML config file. Returns an empty dict if the file does not exist."""
    config_path = Path(path)
    if not config_path.exists():
        return {}
    with config_path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_nested(config: dict, *keys: str, default=None):
    """Safely retrieve a nested config value by key path."""
    current = config
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
        if current is default:
            return default
    return current
