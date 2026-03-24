"""
Pipeline – Query Cache
Cache kết quả pipeline theo question hash.
Nếu user hỏi lại câu giống → trả kết quả ngay, skip LLM.
"""

import os
import hashlib
import json
import logging
from typing import Dict, Any, Optional

from config.settings import EMBEDDING_CACHE_DIR

logger = logging.getLogger(__name__)

_CACHE_FILE = os.path.join(EMBEDDING_CACHE_DIR, "query_cache.json")
_cache: Optional[Dict[str, Any]] = None


def _load_cache() -> Dict[str, Any]:
    """Load cache từ disk."""
    global _cache
    if _cache is not None:
        return _cache

    if os.path.exists(_CACHE_FILE):
        try:
            with open(_CACHE_FILE, "r", encoding="utf-8") as f:
                _cache = json.load(f)
            logger.info(f"[Cache] Loaded {len(_cache)} entries from disk")
        except Exception as e:
            logger.warning(f"[Cache] Failed to load: {e}")
            _cache = {}
    else:
        _cache = {}

    return _cache


def _save_cache():
    """Persist cache to disk."""
    global _cache
    if _cache is None:
        return

    os.makedirs(os.path.dirname(_CACHE_FILE), exist_ok=True)
    try:
        with open(_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.warning(f"[Cache] Failed to save: {e}")


def _hash_question(question: str) -> str:
    """Tạo hash key từ question (normalize whitespace + lowercase)."""
    normalized = " ".join(question.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def _build_cache_key(question: str, domain_id: str | None = None) -> str:
    domain_prefix = (domain_id or "global").strip().lower()
    return f"{domain_prefix}:{_hash_question(question)}"


def get_cached_result(question: str, domain_id: str | None = None) -> Optional[Dict[str, Any]]:
    """
    Tìm kết quả trong cache.
    Returns None nếu miss.
    """
    cache = _load_cache()
    key = _build_cache_key(question, domain_id)
    result = cache.get(key)
    if result:
        logger.info(f"[Cache] HIT for question hash={key}")
        result["cache_hit"] = True
    return result


def cache_result(question: str, result: Dict[str, Any], domain_id: str | None = None):
    """
    Lưu kết quả thành công vào cache.
    Chỉ cache khi validator = PASS hoặc PASS_EMPTY (SQL logic đúng).
    """
    validator = result.get("validator", "")
    if validator not in ("PASS", "PASS_EMPTY"):
        return  # Không cache kết quả lỗi

    cache = _load_cache()
    final_domain = domain_id or result.get("domain")
    key = _build_cache_key(question, final_domain)

    # Chỉ cache các field cần thiết (không cache result_data/result_table)
    cache[key] = {
        "question": question,
        "domain": final_domain,
        "tables": result.get("tables", []),
        "intent": result.get("intent"),
        "entities": result.get("entities", {}),
        "sql": result.get("sql"),
        "validator": result.get("validator"),
    }

    _save_cache()
    logger.info(f"[Cache] Stored result for hash={key}")


def clear_query_cache():
    """Xoá toàn bộ query cache."""
    global _cache
    _cache = {}
    if os.path.exists(_CACHE_FILE):
        os.remove(_CACHE_FILE)
    logger.info("[Cache] Query cache cleared")


def cache_size() -> int:
    """Trả về số entry trong cache."""
    cache = _load_cache()
    return len(cache)
