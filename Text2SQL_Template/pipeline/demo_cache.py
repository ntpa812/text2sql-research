"""
Pipeline – Demo Cache
Lưu kết quả demo khi không kết nối DB thật.
HRM + Banking domain: chạy SQL thật trên SQLite mock.
"""

import json
import logging
import os
import re
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from config.settings import EMBEDDING_CACHE_DIR

logger = logging.getLogger(__name__)

_BASE = Path(__file__).resolve().parent.parent / "data" / "domains"
_HRM_DB_PATH     = _BASE / "hrm"     / "mock" / "hrm.db"
_BANKING_DB_PATH = _BASE / "banking" / "mock" / "banking.db"

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


# ── MySQL → SQLite adapter ────────────────────────────────────────────────────

def _adapt_sql_for_sqlite(sql: str) -> str:
    """
    Chuyển đổi MySQL-specific functions → SQLite tương đương.
    Áp dụng cho banking SQL templates sinh bởi LLM (thường dùng MySQL syntax).
    """
    # MONTH(col) → CAST(strftime('%m', col) AS INTEGER)
    sql = re.sub(
        r'\bMONTH\s*\(\s*([^)]+)\s*\)',
        lambda m: f"CAST(strftime('%m', {m.group(1).strip()}) AS INTEGER)",
        sql, flags=re.IGNORECASE,
    )
    # YEAR(col) → CAST(strftime('%Y', col) AS INTEGER)
    sql = re.sub(
        r'\bYEAR\s*\(\s*([^)]+)\s*\)',
        lambda m: f"CAST(strftime('%Y', {m.group(1).strip()}) AS INTEGER)",
        sql, flags=re.IGNORECASE,
    )
    # EXTRACT(MONTH FROM col) → CAST(strftime('%m', col) AS INTEGER)
    sql = re.sub(
        r'\bEXTRACT\s*\(\s*MONTH\s+FROM\s+([^)]+)\s*\)',
        lambda m: f"CAST(strftime('%m', {m.group(1).strip()}) AS INTEGER)",
        sql, flags=re.IGNORECASE,
    )
    # EXTRACT(YEAR FROM col) → CAST(strftime('%Y', col) AS INTEGER)
    sql = re.sub(
        r'\bEXTRACT\s*\(\s*YEAR\s+FROM\s+([^)]+)\s*\)',
        lambda m: f"CAST(strftime('%Y', {m.group(1).strip()}) AS INTEGER)",
        sql, flags=re.IGNORECASE,
    )
    # CURDATE() / CURRENT_DATE → date('now')
    sql = re.sub(r'\bCURDATE\s*\(\s*\)', "date('now')", sql, flags=re.IGNORECASE)
    sql = re.sub(r'\bCURRENT_DATE\b', "date('now')", sql, flags=re.IGNORECASE)
    # NOW() → datetime('now')
    sql = re.sub(r'\bNOW\s*\(\s*\)', "datetime('now')", sql, flags=re.IGNORECASE)
    # DATE_ADD(expr, INTERVAL n MONTH) → date(expr, '+n month')
    sql = re.sub(
        r'\bDATE_ADD\s*\(\s*([^,]+),\s*INTERVAL\s+(\d+)\s+MONTH\s*\)',
        lambda m: f"date({m.group(1).strip()}, '+{m.group(2)} month')",
        sql, flags=re.IGNORECASE,
    )
    # DATE_ADD(expr, INTERVAL n DAY) → date(expr, '+n day')
    sql = re.sub(
        r'\bDATE_ADD\s*\(\s*([^,]+),\s*INTERVAL\s+(\d+)\s+DAY\s*\)',
        lambda m: f"date({m.group(1).strip()}, '+{m.group(2)} day')",
        sql, flags=re.IGNORECASE,
    )
    # DATE_SUB(expr, INTERVAL n DAY) → date(expr, '-n day')
    sql = re.sub(
        r'\bDATE_SUB\s*\(\s*([^,]+),\s*INTERVAL\s+(\d+)\s+DAY\s*\)',
        lambda m: f"date({m.group(1).strip()}, '-{m.group(2)} day')",
        sql, flags=re.IGNORECASE,
    )
    # DATE_FORMAT(expr, '%Y-%m-01') → strftime('%Y-%m-01', expr)
    sql = re.sub(
        r"\bDATE_FORMAT\s*\(\s*([^,]+),\s*'([^']+)'\s*\)",
        lambda m: f"strftime('{m.group(2)}', {m.group(1).strip()})",
        sql, flags=re.IGNORECASE,
    )
    # `transaction` is a reserved word in SQLite → quote it
    # Match unquoted occurrences: FROM/JOIN transaction (not already quoted)
    sql = re.sub(
        r'(?<!["\w])(\btransaction\b)(?!["\w])',
        '"transaction"',
        sql, flags=re.IGNORECASE,
    )
    return sql


# ── SQLite runner ─────────────────────────────────────────────────────────────

def _run_sqlite(db_path: Path, sql: str, adapt: bool = False) -> List[Dict[str, Any]]:
    if not db_path.exists():
        logger.warning(f"[Demo] DB not found: {db_path}")
        return []
    try:
        adapted = _adapt_sql_for_sqlite(sql) if adapt else sql
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.execute(adapted)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        logger.info(f"[Demo] SQLite ({db_path.name}) returned {len(rows)} rows")
        return rows
    except Exception as exc:
        logger.warning(f"[Demo] SQLite query failed ({db_path.name}): {exc}")
        return []


# ── Public API ────────────────────────────────────────────────────────────────

def get_demo_rows(
    domain_id: str,
    question: str,
    sql: str,
    intent_name: str,
    table_names: List[str],
) -> List[Dict[str, Any]]:
    if not sql or not sql.strip():
        return []

    # HRM: chạy SQL trực tiếp (schema khớp hoàn toàn)
    if domain_id == "hrm":
        return _run_sqlite(_HRM_DB_PATH, sql, adapt=False)

    # Banking: chạy SQL với MySQL→SQLite adapter
    if domain_id == "banking":
        return _run_sqlite(_BANKING_DB_PATH, sql, adapt=True)

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
