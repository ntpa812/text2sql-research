"""
Validator – Data Validator
Kiểm tra data khi SQL trả về 0 rows: entity tồn tại, time range hợp lệ, category hợp lệ.
Có cache để tránh query lặp.
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)

# ─── Entity validation cache (persist trong 1 session) ──────
_entity_cache: Dict[str, bool] = {}


def clear_cache():
    """Xoá cache (dùng khi cần reset)."""
    global _entity_cache
    _entity_cache.clear()


def validate_empty_result(
    sql: str,
    entities: Dict[str, str],
    profiles: Dict[str, Any],
    executor_fn=None,
    domain_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Khi SQL chạy thành công nhưng row = 0, kiểm tra tại sao.

    Returns: {
        "status": "PASS_EMPTY" | "DATA_ERROR",
        "checks": [...],
        "message": str,
    }
    """
    checks: List[Dict[str, Any]] = []

    # Check 1: entity tồn tại trong DB không
    entity_check = _check_entities_exist(entities, profiles, executor_fn, domain_context=domain_context)
    checks.append(entity_check)

    # Check 2: time range hợp lệ
    time_check = _check_time_range(entities, sql)
    checks.append(time_check)

    # Check 3: enum/category hợp lệ
    category_check = _check_categories(entities, profiles, domain_context=domain_context)
    checks.append(category_check)

    # Tổng hợp
    errors = [c for c in checks if c["status"] == "FAIL"]

    if errors:
        messages = [c["message"] for c in errors]
        return {
            "status": "DATA_ERROR",
            "checks": checks,
            "message": "; ".join(messages),
        }

    return {
        "status": "PASS_EMPTY",
        "checks": checks,
        "message": "SQL valid, dữ liệu không tồn tại trong khoảng thời gian/điều kiện đã cho.",
    }


# ─── Check 1: Entity exists in DB ───────────────────────────

# Mapping entity key → (table, column) để kiểm tra tồn tại
ENTITY_TABLE_MAP = {
    "account_no": ("customer_account", "account_no"),
    "to_account_no": ("customer_account", "account_no"),
    "customer_id": ("customer", "customer_id"),
    "trans_id": ("transaction", "trans_id"),
}


def _check_entities_exist(
    entities: Dict[str, str],
    profiles: Dict[str, Any],
    executor_fn=None,
    domain_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Kiểm tra các entity có tồn tại trong DB."""
    global _entity_cache

    if not entities:
        return {"check": "entity_exists", "status": "SKIP", "message": "Không có entity để kiểm tra."}

    entity_table_map = (domain_context or {}).get("entity_table_map", ENTITY_TABLE_MAP)

    # Detect DB engine for correct placeholder
    db_config = (domain_context or {}).get("db_config", {})
    db_engine = db_config.get("engine", "mysql") if isinstance(db_config, dict) else "mysql"
    placeholder = "?" if db_engine == "sqlite" else "%s"

    invalid_entities: List[str] = []

    for key, value in entities.items():
        if key not in entity_table_map:
            continue

        table, column = entity_table_map[key]

        # Check cache trước
        cache_key = f"{table}.{column}={value}"
        if cache_key in _entity_cache:
            if not _entity_cache[cache_key]:
                invalid_entities.append(f"{key}='{value}' không tồn tại trong {table}.{column}")
            continue

        # Check trong DB nếu có executor
        if executor_fn:
            check_sql = f"SELECT 1 FROM {table} WHERE {column} = {placeholder} LIMIT 1"
            try:
                success, rows, err = executor_fn(check_sql, params=[value])
                exists = success and rows and len(rows) > 0
                _entity_cache[cache_key] = exists
                if not exists:
                    invalid_entities.append(f"{key}='{value}' không tồn tại trong {table}.{column}")
            except Exception as e:
                logger.warning(f"[DataValidator] Entity check failed: {e}")
        else:
            # Không có DB → skip
            continue

    if invalid_entities:
        return {
            "check": "entity_exists",
            "status": "FAIL",
            "message": f"Entity không tồn tại: {', '.join(invalid_entities)}",
        }

    return {"check": "entity_exists", "status": "PASS", "message": "Tất cả entities hợp lệ."}


# ─── Check 2: Time range hợp lệ ─────────────────────────────

def _check_time_range(entities: Dict[str, str], sql: str) -> Dict[str, Any]:
    """Kiểm tra time range logic."""
    start_date = entities.get("start_date", "")
    end_date = entities.get("end_date", "")

    if not start_date and not end_date:
        return {"check": "time_range", "status": "SKIP", "message": "Không có time range."}

    # Check start > end
    if start_date and end_date:
        if start_date > end_date:
            return {
                "check": "time_range",
                "status": "FAIL",
                "message": f"start_date ({start_date}) > end_date ({end_date})",
            }

    # Check date ngoài range hợp lý (quá tương lai hoặc quá cũ)
    from datetime import datetime
    try:
        now = datetime.now()
        for label, date_str in [("start_date", start_date), ("end_date", end_date)]:
            if not date_str:
                continue
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            # Quá tương lai (> 1 năm)
            if dt > now.replace(year=now.year + 1):
                return {
                    "check": "time_range",
                    "status": "FAIL",
                    "message": f"{label} ({date_str}) nằm quá xa trong tương lai.",
                }
    except ValueError:
        pass

    return {"check": "time_range", "status": "PASS", "message": "Time range hợp lệ."}


# ─── Check 3: Category/enum hợp lệ ─────────────────────────

KNOWN_ENUMS = {
    "transaction_type": {
        "column": "trans_code",
        "valid_values": [
            "TRANSFER", "SAVING", "LOAN", "FX", "FEE", "BILL_PAYMENT",
            "CK_NOI_BO", "THANH_TOAN_HOA_DON", "CK_LIEN_NH",
        ],
    },
    "status": {
        "column": "status",
        "valid_values": [
            "SUCCESS", "FAILED", "PENDING", "PROCESSING", "REJECTED", "CANCELLED",
        ],
    },
}


def _check_categories(
    entities: Dict[str, str],
    profiles: Dict[str, Any],
    domain_context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Kiểm tra các giá trị enum/category có hợp lệ."""
    known_enums = (domain_context or {}).get("known_enums", KNOWN_ENUMS)
    invalid_cats: List[str] = []

    for key, value in entities.items():
        if key not in known_enums:
            continue

        enum_info = known_enums[key]
        valid = enum_info["valid_values"]

        if value.upper() not in [v.upper() for v in valid]:
            invalid_cats.append(
                f"{key}='{value}' không nằm trong danh sách hợp lệ: {valid}"
            )

    if invalid_cats:
        return {
            "check": "category_valid",
            "status": "FAIL",
            "message": "; ".join(invalid_cats),
        }

    return {"check": "category_valid", "status": "PASS", "message": "Categories hợp lệ."}
