"""
Intent Detection – Intent Loader
Load intent dataset từ JSON, build index cho ranking.
"""

import json
import os
from typing import Dict, List, Any

from config.settings import INTENT_DATASET_PATH


def load_intent_dataset(path: str | None = None) -> List[Dict[str, Any]]:
    """
    Load intent dataset từ file JSON.
    Mỗi item có: document, description, examples, keywords, metadata (SQL template).
    """
    path = path or INTENT_DATASET_PATH
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def build_intent_index(dataset: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
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
            "api_name": parts[0].strip() if len(parts) > 1 else "",
            "description": item.get("description", ""),
            "keywords": item.get("keywords", []),
            "examples": item.get("examples", []),
            "sql_template": item.get("metadata", ""),
        })

    return index


def _normalize_id(text: str) -> str:
    """Normalize text thành intent_id: lowercase, replace spaces with _."""
    import re
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', '_', text)
    return text
