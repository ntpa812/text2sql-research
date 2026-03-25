"""
Entity Extraction – NER Local
Wrapper quanh NER engine từ 6804_DDQ.
Chuẩn hoá output thành dict entity chuẩn cho pipeline.
"""

import os
import sys
import re
import logging
import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# ── Entity type mapping ───────────────────────────────────────────────────────
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

# ── Entity schema for validation ──────────────────────────────────────────────
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

# ══════════════════════════════════════════════════════════════════════════════
# Banking – module-level compiled patterns
# ══════════════════════════════════════════════════════════════════════════════

# Anchored: "tài khoản 123..." / "TK 123..." / "STK 123..."
_BANKING_ACCOUNT_ANCHORED = re.compile(
    r'(?:tài\s*khoản|số\s*(?:tk|tài\s*khoản)|stk)[:\s]+(\d{8,16})',
    re.IGNORECASE,
)
# Bare long number (12+ digits) — realistic VN bank account length
_BANKING_ACCOUNT_BARE = re.compile(r'(?<!\d)(\d{12,16})(?!\d)')

# Recipient account: "đến tài khoản 123..." / "tài khoản người nhận 123..."
_BANKING_TO_ACCOUNT = re.compile(
    r'(?:đến|cho|tài\s*khoản\s*(?:người\s*nhận|đích|nhận|beneficiary))[:\s]+(\d{8,16})',
    re.IGNORECASE,
)

# Money: negative lookbehind prevents matching inside account/ID numbers
_BANKING_MONEY = re.compile(
    r'(?<!\d)(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?|\d+)\s*(triệu|tr|nghìn|ngàn|k|tỷ|tỉ|đồng|đ|vnd)',
    re.IGNORECASE,
)

# ══════════════════════════════════════════════════════════════════════════════
# HRM – module-level compiled patterns
# ══════════════════════════════════════════════════════════════════════════════

# Status enum — longest-match wins (resolved at runtime)
_HRM_STATUS_MAP: Dict[str, str] = {
    # PROBATION
    "đang thử việc":    "PROBATION",
    "thử việc":         "PROBATION",
    "probation":        "PROBATION",
    # ACTIVE
    "đang làm việc":    "ACTIVE",
    "đang công tác":    "ACTIVE",
    "đang hoạt động":   "ACTIVE",
    "còn đang làm":     "ACTIVE",
    "đang làm":         "ACTIVE",
    "còn làm":          "ACTIVE",
    "active":           "ACTIVE",
    # RESIGNED
    "nghỉ việc":        "RESIGNED",
    "thôi việc":        "RESIGNED",
    "đã nghỉ":          "RESIGNED",
    "đã thôi":          "RESIGNED",
    "từ chức":          "RESIGNED",
    "nghỉ hưu":         "RESIGNED",
    "resigned":         "RESIGNED",
    # SUSPENDED
    "tạm đình chỉ":     "SUSPENDED",
    "bị đình chỉ":      "SUSPENDED",
    "đình chỉ":         "SUSPENDED",
    "tạm nghỉ":         "SUSPENDED",
    "suspended":        "SUSPENDED",
}

# Department name: "phòng/ban/bộ phận/tổ/nhóm <tên>"
_DEPT_PATTERN = re.compile(
    r'(?:phòng|ban|bộ\s+phận|tổ|nhóm)\s+([^\s,;?.!\n]+(?:\s+[^\s,;?.!\n]+){0,4})',
    re.IGNORECASE,
)
_DEPT_NOISE = frozenset({"và", "để", "có", "trong", "của", "là", "với", "về", "theo"})

# Employee ID: EMP001, EMP0012, ...
_EMP_ID_PATTERN = re.compile(r'\b(EMP\d{3,})\b', re.IGNORECASE)

# Employee name: "của Nguyễn Văn An" / "nhân viên Nguyễn Văn An"
# Requires the name to start with a Vietnamese family name to avoid matching verb phrases
_VIET_FAMILY_NAMES = (
    r'Nguyễn|Trần|Lê|Phạm|Hoàng|Huỳnh|Phan|Vũ|Võ|Đặng|Bùi|Đỗ|Hồ|Ngô'
    r'|Dương|Lý|Đinh|Hà|Đào|Vương|Cao|Tô|Tạ|Thái|Lưu|Trịnh|Nông|Mạc'
)
_EMP_NAME_PATTERN = re.compile(
    r'(?:của|nhân\s+viên)\s+((?:' + _VIET_FAMILY_NAMES + r')[^\d,;.!?\n]+?)'
    r'(?=\s+(?:ngày|tháng|từ|đến|trong|lúc|vào|theo|có|\d)|[,;.!?]|$)',
    re.IGNORECASE,
)

# Gender
_GENDER_PATTERN = re.compile(r'\b(nam|nữ|male|female)\b', re.IGNORECASE)
_GENDER_MAP: Dict[str, str] = {"nam": "MALE", "male": "MALE", "nữ": "FEMALE", "female": "FEMALE"}

# Salary range: "lương trên 15 triệu" / "lương dưới 20 triệu"
_SALARY_ABOVE = re.compile(
    r'lương\s*(?:trên|>|>=|từ)\s*(\d[\d.,]*)\s*(triệu|tr|nghìn|k|tỷ)',
    re.IGNORECASE,
)
_SALARY_BELOW = re.compile(
    r'lương\s*(?:dưới|<|<=|đến)\s*(\d[\d.,]*)\s*(triệu|tr|nghìn|k|tỷ)',
    re.IGNORECASE,
)

# Date: ISO YYYY-MM-DD
_DATE_ISO = re.compile(r'\b(\d{4}-\d{2}-\d{2})\b')
# Date: DD/MM/YYYY or DD-MM-YYYY
_DATE_DMYSLASH = re.compile(r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b')
# Date: "ngày DD tháng MM [năm YYYY]"
_DATE_WORDS = re.compile(
    r'ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})(?:\s+năm\s+(\d{4}))?',
    re.IGNORECASE,
)

# Date range: "từ YYYY-MM-DD đến YYYY-MM-DD"
_DATE_RANGE_ISO = re.compile(
    r'từ\s+(\d{4}-\d{2}-\d{2})\s+đến\s+(\d{4}-\d{2}-\d{2})',
    re.IGNORECASE,
)
# Date range: "từ DD/MM/YYYY đến DD/MM/YYYY"
_DATE_RANGE_DMYSLASH = re.compile(
    r'từ\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})\s+đến\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
    re.IGNORECASE,
)

# Year-month: "tháng 3" / "tháng 3 năm 2026" / "2026-03" (not followed by -DD)
_YEARMONTH = re.compile(
    r'tháng\s+(\d{1,2})(?:\s+năm\s+(\d{4}))?|(\d{4})-(\d{2})(?!-\d{2})',
    re.IGNORECASE,
)
# Year-only: "năm 2026"
_YEAR_ONLY = re.compile(r'\bnăm\s+(\d{4})\b', re.IGNORECASE)


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

def extract_entities_local(
    question: str,
    domain_id: Optional[str] = None,
) -> Dict[str, str]:
    """
    Extract entities từ câu hỏi bằng NER model local (6804_DDQ).

    Args:
        question:  Câu hỏi tiếng Việt của người dùng.
        domain_id: Domain hiện tại. Accepted values: ``"banking"``, ``"hrm"``.
                   ``None`` → dùng banking patterns.

    Returns:
        Dict entity đã normalize, ví dụ::
            {"account_no": "1234567890", "start_date": "2026-01-01"}
        Trả về ``{}`` nếu không extract được gì.
    """
    raw_entities = _call_ner_engine(question, domain_id=domain_id)
    return _normalize_ner_output(raw_entities)


# ══════════════════════════════════════════════════════════════════════════════
# Internal helpers
# ══════════════════════════════════════════════════════════════════════════════

def _call_ner_engine(question: str, domain_id: Optional[str] = None) -> List[Dict[str, str]]:
    try:
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
    result: Dict[str, str] = {}
    for entity_dict in raw_entities:
        for raw_key, value in entity_dict.items():
            normalized_key = ENTITY_TYPE_MAP.get(raw_key, raw_key)
            if value and str(value).strip():
                result[normalized_key] = str(value).strip()
    return result


def _regex_fallback(question: str, domain_id: Optional[str] = None) -> List[Dict[str, str]]:
    """Route to domain-specific regex extractor. Accepted: "banking" | "hrm"."""
    if domain_id == "hrm":
        return _regex_hrm(question)
    if domain_id not in (None, "banking"):
        logger.warning(f"[NER] Unknown domain_id '{domain_id}', defaulting to banking patterns.")
    return _regex_banking(question)


# ── Banking ───────────────────────────────────────────────────────────────────

def _regex_banking(question: str) -> List[Dict[str, str]]:
    """Banking entity extraction via compiled regex patterns."""
    entities: List[Dict[str, str]] = []

    # Recipient account (check before sender to avoid overlap)
    m = _BANKING_TO_ACCOUNT.search(question)
    if m:
        entities.append({"to_account_no": m.group(1)})

    # Sender account: anchored first, bare long number fallback
    m = _BANKING_ACCOUNT_ANCHORED.search(question)
    if m:
        entities.append({"Số_tài_khoản": m.group(1)})
    else:
        m = _BANKING_ACCOUNT_BARE.search(question)
        if m:
            entities.append({"Số_tài_khoản": m.group(1)})

    # Money amounts
    for m in _BANKING_MONEY.finditer(question):
        entities.append({"Số_tiền": _convert_money(m.group(1), m.group(2))})

    return entities


# ── HRM ───────────────────────────────────────────────────────────────────────

def _regex_hrm(question: str) -> List[Dict[str, str]]:
    """HRM entity extraction via compiled regex patterns."""
    entities: List[Dict[str, str]] = []
    q_lower = question.lower()

    # Employment status — longest match wins
    matched_status, matched_len = None, 0
    for phrase, status_value in _HRM_STATUS_MAP.items():
        if phrase in q_lower and len(phrase) > matched_len:
            matched_status, matched_len = status_value, len(phrase)
    if matched_status:
        entities.append({"employment_status": matched_status})

    # Employee ID
    m = _EMP_ID_PATTERN.search(question)
    if m:
        entities.append({"employee_id": m.group(1).upper()})

    # Employee name
    m = _EMP_NAME_PATTERN.search(question)
    if m:
        name = m.group(1).strip()
        if name:
            entities.append({"employee_name": name})

    # Department name
    m = _DEPT_PATTERN.search(question)
    if m:
        words = m.group(1).strip().split()
        while words and words[-1].lower() in _DEPT_NOISE:
            words.pop()
        dept_name = " ".join(words)
        if dept_name:
            entities.append({"department_name": dept_name})

    # Gender
    m = _GENDER_PATTERN.search(question)
    if m:
        entities.append({"gender": _GENDER_MAP[m.group(1).lower()]})

    # Salary range
    m = _SALARY_ABOVE.search(question)
    if m:
        entities.append({"salary_min": _convert_money(m.group(1), m.group(2))})
    m = _SALARY_BELOW.search(question)
    if m:
        entities.append({"salary_max": _convert_money(m.group(1), m.group(2))})

    # Date range: "từ ... đến ..."
    start_date = end_date = None
    m = _DATE_RANGE_ISO.search(question)
    if m:
        start_date, end_date = m.group(1), m.group(2)
    else:
        m = _DATE_RANGE_DMYSLASH.search(question)
        if m:
            start_date = _parse_dmyslash(m.group(1))
            end_date = _parse_dmyslash(m.group(2))

    if start_date:
        entities.append({"start_date": start_date})
    if end_date:
        entities.append({"end_date": end_date})

    # Single attendance date (only if no range)
    att_date = None
    if not start_date:
        att_date = _extract_attendance_date(question)
        if att_date:
            entities.append({"attendance_date": att_date})

    # Year-month / year-only (only if no full date already found)
    if not att_date and not start_date:
        m = _YEARMONTH.search(question)
        if m:
            if m.group(3) and m.group(4):
                # ISO partial: "2026-03"
                entities.append({"year_month": f"{m.group(3)}-{m.group(4).zfill(2)}"})
            elif m.group(1):
                month = m.group(1).zfill(2)
                year = m.group(2) or str(datetime.date.today().year)
                entities.append({"year_month": f"{year}-{month}"})
        else:
            m = _YEAR_ONLY.search(question)
            if m:
                entities.append({"year_only": m.group(1)})

    # Relative date keywords (only if no date found yet)
    if not att_date and not start_date:
        today = datetime.date.today()
        if "hôm nay" in q_lower or "ngày hôm nay" in q_lower:
            entities.append({"attendance_date": str(today)})
        elif "hôm qua" in q_lower:
            entities.append({"attendance_date": str(today - datetime.timedelta(days=1))})

    return entities


# ── Date helpers ──────────────────────────────────────────────────────────────

def _extract_attendance_date(question: str) -> Optional[str]:
    """Extract a single attendance date (YYYY-MM-DD) from the question."""
    m = _DATE_ISO.search(question)
    if m:
        return m.group(1)
    m = _DATE_DMYSLASH.search(question)
    if m:
        d, mo, y = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
        return f"{y}-{mo}-{d}"
    m = _DATE_WORDS.search(question)
    if m:
        d, mo = m.group(1).zfill(2), m.group(2).zfill(2)
        y = m.group(3) or str(datetime.date.today().year)
        return f"{y}-{mo}-{d}"
    return None


def _parse_dmyslash(date_str: str) -> str:
    """Parse 'DD/MM/YYYY' or 'DD-MM-YYYY' → 'YYYY-MM-DD'."""
    m = re.match(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', date_str.strip())
    if m:
        d, mo, y = m.group(1).zfill(2), m.group(2).zfill(2), m.group(3)
        return f"{y}-{mo}-{d}"
    return date_str


# ── Money helper ──────────────────────────────────────────────────────────────

def _convert_money(num_str: str, unit: str) -> str:
    """
    Convert tiền Việt sang số nguyên (string).

    VN convention:
      '.' = thousand separator  →  1.500 = 1500
      ',' = decimal separator   →  1,5   = 1.5
    """
    if "," in num_str and "." in num_str:
        # Both present: dot = thousand sep, comma = decimal sep
        # e.g. "1.500,50"
        num_str = num_str.replace(".", "").replace(",", ".")
    elif "." in num_str:
        # Dot only = thousand separator: "1.500" → "1500"
        num_str = num_str.replace(".", "")
    elif "," in num_str:
        # Comma only = decimal separator: "1,5" → "1.5"
        num_str = num_str.replace(",", ".")

    try:
        value = float(num_str)
    except ValueError:
        return num_str

    multipliers = {
        "triệu": 1_000_000, "tr": 1_000_000,
        "nghìn": 1_000, "ngàn": 1_000, "k": 1_000,
        "tỷ": 1_000_000_000, "tỉ": 1_000_000_000,
        "đồng": 1, "đ": 1, "vnd": 1,
    }
    value *= multipliers.get(unit.lower(), 1)
    return str(int(value))
