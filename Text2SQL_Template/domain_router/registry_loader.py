"""
Domain Router – Registry Loader
Load registry cấu hình cho từng domain/database.
"""

import json
import os
from copy import deepcopy
from typing import Dict, Any

from config.settings import (
    DEFAULT_DOMAIN_ID,
    DOMAIN_AMBIGUITY_TOLERANCE,
    DOMAIN_REGISTRY_PATH,
    DOMAIN_SHORTLIST_RELATIVE_THRESHOLD,
    DOMAIN_SHORTLIST_SCORE_GAP,
)


def _abspath(base_dir: str, value: str | None) -> str | None:
    if not value:
        return value
    if os.path.isabs(value):
        return value
    return os.path.abspath(os.path.join(base_dir, value))


def load_domain_registry(path: str | None = None) -> Dict[str, Any]:
    registry_path = path or DOMAIN_REGISTRY_PATH
    with open(registry_path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    base_dir = os.path.dirname(registry_path)
    defaults = raw.get("defaults", {})
    result = {
        "default_domain_id": defaults.get("default_domain_id", DEFAULT_DOMAIN_ID),
        "shortlist_score_gap": defaults.get("shortlist_score_gap", DOMAIN_SHORTLIST_SCORE_GAP),
        "shortlist_relative_threshold": defaults.get(
            "shortlist_relative_threshold",
            DOMAIN_SHORTLIST_RELATIVE_THRESHOLD,
        ),
        "ambiguity_tolerance": defaults.get("ambiguity_tolerance", DOMAIN_AMBIGUITY_TOLERANCE),
        "domains": {},
    }

    for item in raw.get("domains", []):
        domain = deepcopy(item)
        domain_id = domain["domain_id"]
        paths = domain.setdefault("paths", {})
        for key in ("semantic_profiles_dir", "intent_dataset_path", "approved_templates_dir"):
            paths[key] = _abspath(base_dir, paths.get(key))
        result["domains"][domain_id] = domain

    if result["default_domain_id"] not in result["domains"] and result["domains"]:
        result["default_domain_id"] = next(iter(result["domains"]))

    return result


def get_domain_config(registry: Dict[str, Any], domain_id: str) -> Dict[str, Any]:
    domains = registry.get("domains", {})
    if domain_id not in domains:
        raise KeyError(f"Unknown domain_id: {domain_id}")
    return domains[domain_id]
