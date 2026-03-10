"""
Entity Extraction – NER Local
Wrapper quanh NER engine từ 6804_DDQ.
Chuẩn hoá output thành dict entity chuẩn cho pipeline.
"""

import os
import sys
import re
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Entity type mapping: NER label → normalized key
ENTITY_TYPE_MAP = {
    "Số_tài_khoản": "account_no",
    "from_date": "start_date",
    "to_date": "end_date",
    "Ngày_giao_dịch": "date_raw",
    "Số_tiền": "amount",
    "Loại_giao_dịch": "transaction_type",
    "Trạng_thái": "status",
    "bank": "bank_name",
    "kênh_giao_dịch": "channel",
    "Tên_người_nhận": "recipient_name",
    "Mã_giao_dịch": "trans_id",
    "Loại_tiền_tệ": "currency",
    "giờ_giao_dịch": "transaction_time",
    "Tên_dịch_vụ": "service_name",
}

# Entity schema for validation
ENTITY_SCHEMA = {
    "account_no": {
        "type": "string",
        "pattern": r"^[0-9]{3,20}$",
        "description": "Bank account number",
    },
    "to_account_no": {
        "type": "string",
        "pattern": r"^[0-9]{3,20}$",
        "description": "Recipient account number",
    },
    "customer_id": {"type": "string"},
    "transaction_type": {
        "type": "enum",
        "values": ["TRANSFER", "SAVING", "LOAN", "FX", "FEE", "BILL_PAYMENT"],
    },
    "amount": {"type": "float"},
    "amount_min": {"type": "float"},
    "amount_max": {"type": "float"},
    "start_date": {"type": "date"},
    "end_date": {"type": "date"},
    "currency": {"type": "string"},
    "status": {"type": "string"},
    "bank_name": {"type": "string"},
    "channel": {"type": "string"},
    "recipient_name": {"type": "string"},
    "trans_id": {"type": "string"},
    "service_name": {"type": "string"},
}


def extract_entities_local(question: str) -> Dict[str, str]:
    """
    Extract entities từ câu hỏi bằng NER model local (6804_DDQ).
    Returns dict đã normalize: { "account_no": "123", "start_date": "2026-01-01", ... }
    """
    raw_entities = _call_ner_engine(question)
    normalized = _normalize_ner_output(raw_entities)
    return normalized


def _call_ner_engine(question: str) -> List[Dict[str, str]]:
    """
    Gọi NER engine từ 6804_DDQ.
    Fallback: trả về list rỗng nếu không load được model.
    """
    try:
        # Add 6804_DDQ to path for import
        ddq_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "6804_DDQ",
        )
        if ddq_path not in sys.path:
            sys.path.insert(0, ddq_path)

        from core.NER.ner_inference import ner_predict

        results = ner_predict(question)
        logger.info(f"[NER] Raw output: {results}")
        return results

    except Exception as e:
        logger.warning(f"[NER] Local NER failed: {e}. Using regex fallback.")
        return _regex_fallback(question)


def _normalize_ner_output(raw_entities: List[Dict[str, str]]) -> Dict[str, str]:
    """
    Chuẩn hoá NER output list → dict thống nhất.
    Input:  [{"Số_tài_khoản": "123"}, {"from_date": "2026-01-01"}, ...]
    Output: {"account_no": "123", "start_date": "2026-01-01", ...}
    """
    result: Dict[str, str] = {}

    for entity_dict in raw_entities:
        for raw_key, value in entity_dict.items():
            normalized_key = ENTITY_TYPE_MAP.get(raw_key, raw_key)
            if value and str(value).strip():
                result[normalized_key] = str(value).strip()

    return result


def _regex_fallback(question: str) -> List[Dict[str, str]]:
    """
    Regex-based entity extraction fallback khi NER model không available.
    """
    entities: List[Dict[str, str]] = []

    # Account number: dãy số 6-20 ký tự
    for match in re.finditer(r'\b(\d{6,20})\b', question):
        entities.append({"Số_tài_khoản": match.group(1)})

    # Money: số + đơn vị tiền
    money_pattern = r'(\d[\d.,]*)\s*(triệu|tr|nghìn|ngàn|k|tỷ|tỉ|đồng|đ|vnd)'
    for match in re.finditer(money_pattern, question, re.IGNORECASE):
        entities.append({"Số_tiền": _convert_money(match.group(1), match.group(2))})

    return entities


def _convert_money(num_str: str, unit: str) -> str:
    """Convert tiền Việt sang dạng số."""
    num_str = num_str.replace(",", "").replace(".", "")
    try:
        value = float(num_str)
    except ValueError:
        return num_str

    unit_lower = unit.lower()
    multipliers = {
        "triệu": 1_000_000, "tr": 1_000_000,
        "nghìn": 1_000, "ngàn": 1_000, "k": 1_000,
        "tỷ": 1_000_000_000, "tỉ": 1_000_000_000,
        "đồng": 1, "đ": 1, "vnd": 1,
    }
    value *= multipliers.get(unit_lower, 1)
    return str(int(value))
