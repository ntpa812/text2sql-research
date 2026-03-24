"""
Intent Detection – Intent Loader
Load intent dataset từ JSON, build index cho ranking.
"""

import json
import os
from typing import Dict, List, Any

from config.settings import DEFAULT_DOMAIN_ID, LEGACY_INTENT_DATASET_PATH


def _clean_sql_template(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = value.strip()
    if cleaned.lower() in {"nan", "none", "null"}:
        return ""
    return cleaned


def _resolve_intent_path(path: str | None = None, domain_id: str | None = None) -> str:
    if path:
        return path

    domain_id = domain_id or DEFAULT_DOMAIN_ID
    domain_candidate = os.path.join(
        os.path.dirname(os.path.dirname(LEGACY_INTENT_DATASET_PATH)),
        "domains",
        domain_id,
        "user_intent",
        os.path.basename(LEGACY_INTENT_DATASET_PATH),
    )
    if os.path.isfile(domain_candidate):
        return domain_candidate
    return LEGACY_INTENT_DATASET_PATH


def load_intent_dataset(path: str | None = None, domain_id: str | None = None) -> List[Dict[str, Any]]:
    """
    Load intent dataset từ file JSON.
    Mỗi item có: document, description, examples, keywords, metadata (SQL template).
    """
    path = _resolve_intent_path(path, domain_id)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def build_intent_index(dataset: List[Dict[str, Any]], domain_id: str | None = None) -> List[Dict[str, Any]]:
    """
    Build intent index từ dataset.
    Tạo intent_id từ document field, gom keywords + examples.
    """
    index: List[Dict[str, Any]] = []

    for i, item in enumerate(dataset):
        doc = item.get("document", "")
        # intent_id: lấy phần sau dấu "|" và normalize
        parts = doc.split("|")
        intent_name = parts[-1].strip() if len(parts) > 1 else doc.strip()
        intent_id = _normalize_id(intent_name)

        index.append({
            "index": i,
            "intent_id": intent_id,
            "intent_name": intent_name,
            "domain_id": domain_id or DEFAULT_DOMAIN_ID,
            "api_name": parts[0].strip() if len(parts) > 1 else "",
            "description": item.get("description", ""),
            "keywords": item.get("keywords", []),
            "examples": item.get("examples", []),
            "sql_template": _clean_sql_template(item.get("metadata", "")),
        })

    return index


def _normalize_id(text: str) -> str:
    """Normalize text thành intent_id: lowercase, replace spaces with _."""
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', '_', text)
    return text
