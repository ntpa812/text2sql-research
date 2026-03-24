"""
Pipeline – Demo Cache
Lưu kết quả demo khi không kết nối DB thật.
"""

import json
import os
import hashlib
from datetime import datetime
from typing import Any, Dict, List

from config.settings import EMBEDDING_CACHE_DIR

_DEMO_CACHE_FILE = os.path.join(EMBEDDING_CACHE_DIR, "demo_execution_cache.json")
_demo_cache: Dict[str, Any] | None = None


def _load_cache() -> Dict[str, Any]:
    global _demo_cache
    if _demo_cache is not None:
        return _demo_cache

    if os.path.isfile(_DEMO_CACHE_FILE):
        with open(_DEMO_CACHE_FILE, "r", encoding="utf-8") as f:
            _demo_cache = json.load(f)
    else:
        _demo_cache = {}
    return _demo_cache


def _save_cache():
    global _demo_cache
    if _demo_cache is None:
        return
    os.makedirs(os.path.dirname(_DEMO_CACHE_FILE), exist_ok=True)
    with open(_DEMO_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(_demo_cache, f, ensure_ascii=False, indent=2)


def _build_key(domain_id: str, question: str) -> str:
    normalized = f"{domain_id}:{' '.join(question.lower().split())}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:20]


def get_demo_rows(
    domain_id: str,
    question: str,
    sql: str,
    intent_name: str,
    table_names: List[str],
) -> List[Dict[str, Any]]:
    cache = _load_cache()
    key = _build_key(domain_id, question)
    if key in cache:
        return cache[key]["rows"]

    rows = [
        {
            "demo_id": key[:8],
            "domain": domain_id,
            "intent": intent_name or "unknown",
            "tables": ", ".join(table_names),
            "preview_sql": sql[:160],
            "note": "Demo mode: ket qua duoc luu local cache, khong truy cap DB that.",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        }
    ]
    cache[key] = {
        "question": question,
        "domain": domain_id,
        "rows": rows,
    }
    _save_cache()
    return rows
