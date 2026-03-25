"""
Slot Filling – Entity Normalizer
Chuẩn hoá entities thô → dạng chuẩn (date, amount, enum).
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Transaction type mapping: Vietnamese → DB enum
TRANSACTION_TYPE_MAP = {
    "chuyển tiền": "TRANSFER",
    "chuyển khoản": "TRANSFER",
    "chuyển": "TRANSFER",
    "tiết kiệm": "SAVING",
    "gửi tiết kiệm": "SAVING",
    "vay": "LOAN",
    "khoản vay": "LOAN",
    "ngoại tệ": "FX",
    "đổi tiền": "FX",
    "phí": "FEE",
    "thanh toán hóa đơn": "BILL_PAYMENT",
    "hóa đơn": "BILL_PAYMENT",
}

# Status mapping: Vietnamese → DB enum
STATUS_MAP = {
    "thành công": "SUCCESS",
    "hoàn tất": "SUCCESS",
    "thất bại": "FAILED",
    "lỗi": "FAILED",
    "bị lỗi": "FAILED",
    "chờ xử lý": "PENDING",
    "đang xử lý": "PROCESSING",
    "bị từ chối": "REJECTED",
    "đã hủy": "CANCELLED",
    "hủy": "CANCELLED",
}


def normalize_entities(entities: Dict[str, str]) -> Dict[str, str]:
    """
    Chuẩn hoá toàn bộ dict entities.
    Áp dụng normalization cho từng loại entity.
    """
    normalized: Dict[str, str] = {}

    for key, value in entities.items():
        if not value or not str(value).strip():
            continue

        value = str(value).strip()

        if key in ("start_date", "end_date"):
            normalized[key] = _normalize_date(value)
        elif key in ("amount", "amount_min", "amount_max"):
            normalized[key] = _normalize_amount(value)
        elif key == "transaction_type":
            normalized[key] = _normalize_transaction_type(value)
        elif key == "status":
            normalized[key] = _normalize_status(value)
        elif key in ("account_no", "to_account_no"):
            normalized[key] = _normalize_account(value)
        else:
            normalized[key] = value

    return normalized


def _normalize_date(value: str) -> str:
    """Chuẩn hoá date string → YYYY-MM-DD."""
    # Nếu đã ở dạng YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}$', value):
        return value

    # DD/MM/YYYY
    m = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', value)
    if m:
        return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"

    return value


def _normalize_amount(value: str) -> str:
    """Chuẩn hoá số tiền → dạng số."""
    # Loại bỏ ký tự không phải số
    cleaned = re.sub(r'[^\d.]', '', value)
    if cleaned:
        try:
            return str(int(float(cleaned)))
        except ValueError:
            pass
    return value


def _normalize_transaction_type(value: str) -> str:
    """Chuẩn hoá loại giao dịch → DB enum."""
    value_lower = value.lower().strip()
    for vn_text, db_enum in TRANSACTION_TYPE_MAP.items():
        if vn_text in value_lower:
            return db_enum
    return value.upper()


def _normalize_status(value: str) -> str:
    """Chuẩn hoá trạng thái → DB enum."""
    value_lower = value.lower().strip()
    for vn_text, db_enum in STATUS_MAP.items():
        if vn_text in value_lower:
            return db_enum
    return value.upper()


def _normalize_account(value: str) -> str:
    """Chuẩn hoá số tài khoản: chỉ giữ digits."""
    digits = re.sub(r'\D', '', value)
    return digits if digits else value
