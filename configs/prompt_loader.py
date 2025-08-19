# -*- coding: utf-8 -*-
"""
Lightweight prompt loader with simple in-process cache.
Loads YAML prompts from configs/prompts/*.yaml
"""
from __future__ import annotations
import os
from typing import Dict, Any, Optional

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # optional dependency; callers should handle None content

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
_PROMPT_DIR = os.path.join(_BASE_DIR, "configs", "prompts")
_CACHE: Dict[str, Dict[str, Any]] = {}


def _prompt_path(name: str) -> str:
    return os.path.join(_PROMPT_DIR, f"{name}.yaml")


def load_prompt(name: str) -> Optional[Dict[str, Any]]:
    """Load a prompt YAML by name. Returns dict or None if missing or yaml unavailable.

    Args:
        name: prompt file basename without extension (e.g., 'coordinator').
    """
    if name in _CACHE:
        return _CACHE[name]
    path = _prompt_path(name)
    if not os.path.exists(path) or yaml is None:
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    _CACHE[name] = data
    return data


def get_prompt_text(name: str, default: str = "") -> str:
    """Convenience to extract content text from prompt YAML.

    Falls back to default if YAML not present or invalid.
    """
    data = load_prompt(name)
    if not data:
        return default
    return str(data.get("content", default))


# --- Lightweight schema helpers (optional use) ---
def _is_mapping(obj: Any) -> bool:  # type: ignore[name-defined]
    try:
        return isinstance(obj, dict)
    except Exception:
        return False


def require_keys(d: Dict[str, Any], keys: Any) -> bool:
    """Return True if all keys exist in dict d."""
    if not _is_mapping(d):
        return False
    return all(k in d for k in keys)


def validate_subtasks_config(data: Optional[Dict[str, Any]]) -> bool:
    """Validate subtasks.yaml structure.

    Expected shape:
    {
      "items": [
        {"id_suffix": str, "type": str, "description": str, "content": str, "priority": str?, "depends_on": [str]?}, ...
      ]
    }
    """
    if not _is_mapping(data):
        return False
    items = data.get("items")
    if not isinstance(items, list) or not items:
        return False
    for it in items:
        if not _is_mapping(it):
            return False
        if not require_keys(it, ["id_suffix", "type", "content"]):
            return False
        # content must be str to allow .format(user_request=...)
        if not isinstance(it.get("content"), str):
            return False
    return True
