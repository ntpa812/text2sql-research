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


def extract_entities_local(question: str, domain_id: Optional[str] = None) -> Dict[str, str]:
    """
    Extract entities từ câu hỏi bằng NER model local (6804_DDQ).
    Returns dict đã normalize: { "account_no": "123", "start_date": "2026-01-01", ... }
    """
    raw_entities = _call_ner_engine(question, domain_id=domain_id)
    normalized = _normalize_ner_output(raw_entities)
    return normalized


def _call_ner_engine(question: str, domain_id: Optional[str] = None) -> List[Dict[str, str]]:
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
        return _regex_fallback(question, domain_id=domain_id)


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


def _regex_fallback(question: str, domain_id: Optional[str] = None) -> List[Dict[str, str]]:
    """
    Regex-based entity extraction fallback khi NER model không available.
    Hỗ trợ banking và hrm domain.
    """
    entities: List[Dict[str, str]] = []

    if domain_id == "hrm":
        entities.extend(_regex_hrm(question))
    else:
        # Banking patterns
        # Account number: dãy số 6-20 ký tự
        for match in re.finditer(r'\b(\d{6,20})\b', question):
            entities.append({"Số_tài_khoản": match.group(1)})

        # Money: số + đơn vị tiền
        money_pattern = r'(\d[\d.,]*)\s*(triệu|tr|nghìn|ngàn|k|tỷ|tỉ|đồng|đ|vnd)'
        for match in re.finditer(money_pattern, question, re.IGNORECASE):
            entities.append({"Số_tiền": _convert_money(match.group(1), match.group(2))})

    return entities


# ── HRM status enum mapping ───────────────────────────────────────────────────
_HRM_STATUS_MAP = {
    "thử việc":      "PROBATION",
    "probation":     "PROBATION",
    "đang làm":      "ACTIVE",
    "đang công tác": "ACTIVE",
    "đang hoạt động":"ACTIVE",
    "active":        "ACTIVE",
    "nghỉ việc":     "RESIGNED",
    "thôi việc":     "RESIGNED",
    "đã nghỉ":       "RESIGNED",
    "đã thôi":       "RESIGNED",
    "từ chức":       "RESIGNED",
    "resigned":      "RESIGNED",
    "đình chỉ":      "SUSPENDED",
    "tạm đình chỉ":  "SUSPENDED",
    "suspended":     "SUSPENDED",
}

# ── HRM department name patterns ─────────────────────────────────────────────
_DEPT_PATTERN = re.compile(
    r'(?:phòng|ban|bộ phận|tổ|nhóm)\s+([^\s,;?.!]+(?:\s+[^\s,;?.!]+){0,4})',
    re.IGNORECASE,
)

# ── HRM employee ID pattern ───────────────────────────────────────────────────
_EMP_ID_PATTERN = re.compile(r'\bEMP\d{3,}\b', re.IGNORECASE)

# ── Year-month patterns ───────────────────────────────────────────────────────
_YEARMONTH_PATTERN = re.compile(
    r'tháng\s+(\d{1,2})(?:\s+năm\s+(\d{4}))?|(\d{4})-(\d{2})',
    re.IGNORECASE,
)

# ── Attendance date patterns ──────────────────────────────────────────────────
# ISO: 2026-03-24
_DATE_ISO_PATTERN = re.compile(r'\b(\d{4}-\d{2}-\d{2})\b')
# DD/MM/YYYY or DD-MM-YYYY
_DATE_DMYSLASH_PATTERN = re.compile(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b')
# "ngày DD tháng MM [năm YYYY]"
_DATE_WORDS_PATTERN = re.compile(
    r'ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})(?:\s+năm\s+(\d{4}))?',
    re.IGNORECASE,
)

# ── Employee name pattern ─────────────────────────────────────────────────────
# "của Nguyễn Văn An ngày/..." or "nhân viên Nguyễn Văn An"
_EMP_NAME_PATTERN = re.compile(
    r'(?:của|nhân\s+viên)\s+([^\d,;.!?\n]+?)(?=\s+(?:ngày|tháng|từ|đến|trong|lúc|vào|theo|có|\d)|[,;.!?]|$)',
    re.IGNORECASE,
)


def _extract_attendance_date(question: str) -> str | None:
    """Extract a single attendance date (YYYY-MM-DD) from the question."""
    # ISO: 2026-03-24
    m = _DATE_ISO_PATTERN.search(question)
    if m:
        return m.group(1)
    # DD/MM/YYYY or DD-MM-YYYY
    m = _DATE_DMYSLASH_PATTERN.search(question)
    if m:
        d, mo, y = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
        return f"{y}-{mo}-{d}"
    # "ngày DD tháng MM [năm YYYY]"
    m = _DATE_WORDS_PATTERN.search(question)
    if m:
        d, mo = m.group(1).zfill(2), m.group(2).zfill(2)
        y = m.group(3) or "2026"
        return f"{y}-{mo}-{d}"
    return None


def _regex_hrm(question: str) -> List[Dict[str, str]]:
    """HRM-specific regex entity extraction."""
    entities: List[Dict[str, str]] = []
    q_lower = question.lower()

    # Employment status
    for phrase, status_value in _HRM_STATUS_MAP.items():
        if phrase in q_lower:
            entities.append({"employment_status": status_value})
            break

    # Employee ID (EMP001)
    for match in _EMP_ID_PATTERN.finditer(question):
        entities.append({"employee_id": match.group(0).upper()})
        break

    # Employee name: "của Nguyễn Văn An" / "nhân viên Nguyễn Văn An"
    name_match = _EMP_NAME_PATTERN.search(question)
    if name_match:
        name = name_match.group(1).strip()
        if name:
            entities.append({"employee_name": name})

    # Department name: extract text after "phòng/ban/bộ phận"
    dept_match = _DEPT_PATTERN.search(question)
    if dept_match:
        dept_name = dept_match.group(1).strip()
        # Remove trailing noise words
        for noise in ["và", "để", "có", "trong", "của", "là"]:
            if dept_name.lower().endswith(" " + noise):
                dept_name = dept_name[: -(len(noise) + 1)].strip()
        entities.append({"department_name": dept_name})

    # Attendance date (explicit)
    att_date = _extract_attendance_date(question)
    if att_date:
        entities.append({"attendance_date": att_date})

    # Year-month: "tháng 3" / "tháng 3 năm 2026" / "2026-03"
    # Only if no full date was already found
    if not att_date:
        ym_match = _YEARMONTH_PATTERN.search(question)
        if ym_match:
            if ym_match.group(3) and ym_match.group(4):
                entities.append({"year_month": f"{ym_match.group(3)}-{ym_match.group(4).zfill(2)}"})
            elif ym_match.group(1):
                month = ym_match.group(1).zfill(2)
                year = ym_match.group(2) or "2026"
                entities.append({"year_month": f"{year}-{month}"})

    # Date keywords
    import datetime
    today = datetime.date.today()
    if not att_date:
        if "hôm nay" in q_lower or "ngày hôm nay" in q_lower:
            entities.append({"attendance_date": str(today)})
        elif "hôm qua" in q_lower:
            entities.append({"attendance_date": str(today - datetime.timedelta(days=1))})

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
