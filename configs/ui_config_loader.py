# -*- coding: utf-8 -*-
"""
Lightweight UI config loader. Loads YAML from configs/ui/*.yaml
Provides safe fallbacks when files are missing or PyYAML is unavailable.
"""
from __future__ import annotations
import os
from typing import Any, Dict, Optional, List

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
_UI_DIR = os.path.join(_BASE_DIR, "configs", "ui")
_CACHE: Dict[str, Dict[str, Any]] = {}


def _ui_path(name: str) -> str:
    return os.path.join(_UI_DIR, f"{name}.yaml")


def load_ui_config(name: str) -> Optional[Dict[str, Any]]:
    if name in _CACHE:
        return _CACHE[name]
    path = _ui_path(name)
    if not os.path.exists(path) or yaml is None:
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    _CACHE[name] = data
    return data


def get_ui_config(name: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = load_ui_config(name)
    if not isinstance(data, dict):
        return default or {}
    # Apply schema validation for known UI configs
    if name == "prompt_options":
        return _validate_prompt_options(data, default or {})
    return data


# --- Validation helpers ---
def _as_list_str(val: Any, fallback: List[str]) -> List[str]:
    if isinstance(val, list):
        return [str(x) for x in val if isinstance(x, (str, int, float))]
    return list(fallback)


def _validate_prompt_options(data: Dict[str, Any], default: Dict[str, Any]) -> Dict[str, Any]:
    """Validate and coerce the structure of prompt_options.yaml.
    Expected shape:
      basic:
        domains: [str]
        tones: [str]
        output_formats: [str]
        examples_default: bool
      advanced:
        domains: [str]
        complexity_options: [str]
        creativity: {min:int, max:int, default:int}
        examples_default: bool
        include_context_default: bool
    """
    out: Dict[str, Any] = {}
    basic = data.get("basic", {}) if isinstance(data.get("basic"), dict) else {}
    adv = data.get("advanced", {}) if isinstance(data.get("advanced"), dict) else {}

    # Basic section
    out_basic: Dict[str, Any] = {}
    out_basic["domains"] = _as_list_str(
        basic.get("domains"), default.get("basic", {}).get("domains", ["일반", "마케팅", "개발", "디자인", "교육", "비즈니스"])  # type: ignore[arg-type]
    )
    out_basic["tones"] = _as_list_str(
        basic.get("tones"), default.get("basic", {}).get("tones", ["전문적", "친근한", "격식있는", "창의적", "간결한"])  # type: ignore[arg-type]
    )
    out_basic["output_formats"] = _as_list_str(
        basic.get("output_formats"), default.get("basic", {}).get("output_formats", ["일반 텍스트", "목록", "표", "에세이", "코드"])  # type: ignore[arg-type]
    )
    out_basic["examples_default"] = bool(basic.get("examples_default", default.get("basic", {}).get("examples_default", True)))

    # Advanced section
    out_adv: Dict[str, Any] = {}
    out_adv["domains"] = _as_list_str(
        adv.get("domains"), default.get("advanced", {}).get("domains", out_basic["domains"])  # type: ignore[arg-type]
    )
    out_adv["complexity_options"] = _as_list_str(
        adv.get("complexity_options"), default.get("advanced", {}).get("complexity_options", ["간단", "보통", "복잡", "매우 복잡"])  # type: ignore[arg-type]
    )
    # Creativity
    cre = adv.get("creativity") if isinstance(adv.get("creativity"), dict) else {}
    cmin = int(cre.get("min", 0) if isinstance(cre.get("min"), (int, float)) else 0)
    cmax = int(cre.get("max", 10) if isinstance(cre.get("max"), (int, float)) else 10)
    cdef = int(cre.get("default", 5) if isinstance(cre.get("default"), (int, float)) else 5)
    # Clamp defaults
    if cmin > cmax:
        cmin, cmax = 0, 10
    cdef = max(cmin, min(cdef, cmax))
    out_adv["creativity"] = {"min": cmin, "max": cmax, "default": cdef}
    out_adv["examples_default"] = bool(adv.get("examples_default", default.get("advanced", {}).get("examples_default", True)))
    out_adv["include_context_default"] = bool(adv.get("include_context_default", default.get("advanced", {}).get("include_context_default", False)))

    out["basic"] = out_basic
    out["advanced"] = out_adv
    return out
