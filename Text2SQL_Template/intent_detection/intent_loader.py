"""
Intent Detection – Intent Loader
Load intent dataset từ JSON, build index cho ranking.
Cache dataset và index theo đường dẫn file để tránh re-read từ disk mỗi request.
"""

import json
import os
import re
from typing import Dict, List, Any, Optional

from config.settings import DEFAULT_DOMAIN_ID, LEGACY_INTENT_DATASET_PATH

# Module-level cache: { file_path -> raw dataset list }
_dataset_cache: Dict[str, List[Dict[str, Any]]] = {}

# Module-level cache: { cache_key -> intent index list }
# cache_key = f"{file_path}::{domain_id}"
_index_cache: Dict[str, List[Dict[str, Any]]] = {}


def _clean_sql_template(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    cleaned = value.strip()
    if cleaned.lower() in {"nan", "none", "null"}:
        return ""
    return cleaned


def _resolve_intent_path(path: Optional[str] = None, domain_id: Optional[str] = None) -> str:
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


def _normalize_id(text: str) -> str:
    """Normalize text thành intent_id: lowercase, replace spaces with _."""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', '_', text)
    return text


def load_intent_dataset(path: Optional[str] = None, domain_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Load intent dataset từ file JSON.
    Kết quả được cache theo đường dẫn file — chỉ đọc disk lần đầu tiên.
    """
    resolved_path = _resolve_intent_path(path, domain_id)

    if resolved_path not in _dataset_cache:
        with open(resolved_path, "r", encoding="utf-8") as f:
            _dataset_cache[resolved_path] = json.load(f)

    return _dataset_cache[resolved_path]


def build_intent_index(dataset: List[Dict[str, Any]], domain_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Build intent index từ dataset.
    Tạo intent_id từ document field, gom keywords + examples.
    Kết quả được cache theo (dataset id, domain_id).
    """
    cache_key = f"{id(dataset)}::{domain_id}"

    if cache_key not in _index_cache:
        _index_cache[cache_key] = _build_index(dataset, domain_id)

    return _index_cache[cache_key]


def _build_index(dataset: List[Dict[str, Any]], domain_id: Optional[str]) -> List[Dict[str, Any]]:
    index: List[Dict[str, Any]] = []

    for i, item in enumerate(dataset):
        doc = item.get("document", "")
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


def clear_cache() -> None:
    """Xoá cache (dùng khi reload config hoặc trong tests)."""
    _dataset_cache.clear()
    _index_cache.clear()
