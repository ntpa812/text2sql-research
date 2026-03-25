"""
Pipeline – Demo Cache
Lưu kết quả demo khi không kết nối DB thật.
HRM domain: chạy SQL thật trên SQLite.
"""

import json
import logging
import os
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from config.settings import EMBEDDING_CACHE_DIR

logger = logging.getLogger(__name__)

_HRM_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "domains" / "hrm" / "mock" / "hrm.db"

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


def _run_hrm_sqlite(sql: str) -> List[Dict[str, Any]]:
    """Chạy SQL trực tiếp trên HRM SQLite database."""
    if not _HRM_DB_PATH.exists():
        logger.warning(f"[Demo] HRM DB not found at {_HRM_DB_PATH}")
        return []
    try:
        conn = sqlite3.connect(_HRM_DB_PATH)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(sql)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        logger.info(f"[Demo] HRM SQLite returned {len(rows)} rows")
        return rows
    except Exception as exc:
        logger.warning(f"[Demo] HRM SQLite query failed: {exc}")
        return []


def get_demo_rows(
    domain_id: str,
    question: str,
    sql: str,
    intent_name: str,
    table_names: List[str],
) -> List[Dict[str, Any]]:
    # HRM domain: chạy SQL thật trên SQLite
    if domain_id == "hrm" and sql and sql.strip():
        return _run_hrm_sqlite(sql)

    # Các domain khác: dùng cache placeholder
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
    cache[key] = {"question": question, "domain": domain_id, "rows": rows}
    _save_cache()
    return rows
