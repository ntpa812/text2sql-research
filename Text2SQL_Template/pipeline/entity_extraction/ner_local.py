"""
Entity Extraction – NER Local
Wrapper quanh NER engine từ 6804_DDQ.
Chuẩn hoá output thành dict entity chuẩn cho pipeline.
"""

import os
import sys
import re
import calendar
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
# Shared – Vietnamese family names (used by both banking and HRM)
# ══════════════════════════════════════════════════════════════════════════════
_VIET_FAMILY_NAMES = (
    r'Nguyễn|Trần|Lê|Phạm|Hoàng|Huỳnh|Phan|Vũ|Võ|Đặng|Bùi|Đỗ|Hồ|Ngô'
    r'|Dương|Lý|Đinh|Hà|Đào|Vương|Cao|Tô|Tạ|Thái|Lưu|Trịnh|Nông|Mạc'
)

# ══════════════════════════════════════════════════════════════════════════════
# Banking – module-level compiled patterns
# ══════════════════════════════════════════════════════════════════════════════

# Anchored: "tài khoản 123..." / "TK 123..." / "STK 123..."
_BANKING_ACCOUNT_ANCHORED = re.compile(
    r'(?:tài\s*khoản|số\s*(?:tk|tài\s*khoản)|stk|tk)[:\s]+(\d{6,16})',
    re.IGNORECASE,
)
# Bare long number (10+ digits) — realistic VN bank account length
_BANKING_ACCOUNT_BARE = re.compile(r'(?<!\d)(\d{10,16})(?!\d)')

# Recipient account: "đến tài khoản 123..." / "tài khoản người nhận 123..."
_BANKING_TO_ACCOUNT = re.compile(
    r'(?:đến|cho|tới)\s+(?:tài\s*khoản|tk|stk)[:\s]+(\d{6,16})'
    r'|(?:tài\s*khoản\s*(?:người\s*nhận|đích|nhận|beneficiary))[:\s]+(\d{6,16})',
    re.IGNORECASE,
)

# Money: must be followed by a currency unit — avoids matching bare years/IDs
_BANKING_MONEY = re.compile(
    r'(?<!\d)(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?|\d+)\s*(triệu|tr|nghìn|ngàn|k|tỷ|tỉ|đồng|đ|vnd)\b',
    re.IGNORECASE,
)

# Money range: "từ 2 triệu đến 10 triệu" / "từ 5tr - 20tr"
_BANKING_MONEY_RANGE = re.compile(
    r'(?:từ|trên|>=?)\s*(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?|\d+)\s*(triệu|tr|nghìn|ngàn|k|tỷ|tỉ|đồng|đ|vnd)'
    r'\s*(?:đến|tới|->|-|~)\s*'
    r'(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d+)?|\d+)\s*(triệu|tr|nghìn|ngàn|k|tỷ|tỉ|đồng|đ|vnd)',
    re.IGNORECASE,
)

# ── Date patterns (banking) ──────────────────────────────────────────────────

# Date range: "từ 01/03/2025 đến 31/03/2025" or "từ 2025-01-01 đến 2025-03-31"
_BK_DATE_RANGE_ISO = re.compile(
    r'từ\s+(\d{4}-\d{1,2}-\d{1,2})\s+(?:đến|tới|->)\s+(\d{4}-\d{1,2}-\d{1,2})',
    re.IGNORECASE,
)
_BK_DATE_RANGE_DMY = re.compile(
    r'từ\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})\s+(?:đến|tới|->)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
    re.IGNORECASE,
)
# "từ ngày 1 tháng 3 đến ngày 31 tháng 3 [năm 2025]"
_BK_DATE_RANGE_WORDS = re.compile(
    r'từ\s+(?:ngày\s+)?(\d{1,2})\s*[/-]?\s*(?:tháng\s+)?(\d{1,2})(?:\s*[/-]?\s*(?:năm\s+)?(\d{4}))?'
    r'\s+(?:đến|tới)\s+(?:ngày\s+)?(\d{1,2})\s*[/-]?\s*(?:tháng\s+)?(\d{1,2})(?:\s*[/-]?\s*(?:năm\s+)?(\d{4}))?',
    re.IGNORECASE,
)

# Single date: "ngày 15/03/2025" / "ngày 15 tháng 3 năm 2025"
_BK_DATE_ISO = re.compile(r'\b(\d{4}-\d{1,2}-\d{1,2})\b')
_BK_DATE_DMY = re.compile(r'(?:ngày\s+)?(\d{1,2})[/-](\d{1,2})[/-](\d{4})')
_BK_DATE_WORDS = re.compile(
    r'ngày\s+(\d{1,2})\s+tháng\s+(\d{1,2})(?:\s+năm\s+(\d{4}))?',
    re.IGNORECASE,
)

# Relative time: "3 ngày trước", "tuần trước", "tháng này", "năm ngoái", "quý 1"
_BK_RELATIVE_PERIOD = re.compile(
    r'(\d+)\s+(ngày|tuần|tháng|năm)\s+(trước|qua|gần đây|gần nhất|vừa qua|nay|gần)',
    re.IGNORECASE,
)
_BK_NAMED_PERIOD = re.compile(
    r'(hôm nay|hôm qua|tuần (?:này|trước|qua)|tháng (?:này|trước|qua|rồi)'
    r'|năm (?:nay|ngoái|trước|qua)|quý (?:này|trước|qua|[1-4])'
    r'|đầu tháng|cuối tháng|đầu năm|cuối năm'
    r'|(?:3|6|7|30|60|90) ngày (?:trước|qua|gần đây|gần nhất))',
    re.IGNORECASE,
)

# "tháng 3" / "tháng 3 năm 2025" / "tháng 03/2025"
_BK_YEARMONTH = re.compile(
    r'tháng\s+(\d{1,2})(?:\s*[/-]\s*|\s+năm\s+)(\d{4})'
    r'|tháng\s+(\d{1,2})(?!\s*[/-]\s*\d)',
    re.IGNORECASE,
)
# "năm 2025" (standalone / fallback) — resolved at runtime to skip "tháng X năm Y"
_BK_YEAR_ONLY = re.compile(r'\bnăm\s+(\d{4})\b', re.IGNORECASE)
_BK_YEAR_FALLBACK = _BK_YEAR_ONLY

# ── Transaction type ─────────────────────────────────────────────────────────
_BK_TRANS_TYPE_MAP: Dict[str, str] = {
    "chuyển tiền": "TRANSFER", "chuyển khoản": "TRANSFER", "chuyển": "TRANSFER",
    "transfer": "TRANSFER",
    "tiết kiệm": "SAVING", "gửi tiết kiệm": "SAVING", "saving": "SAVING",
    "vay": "LOAN", "khoản vay": "LOAN", "loan": "LOAN",
    "ngoại tệ": "FX", "ngoại hối": "FX", "forex": "FX", "fx": "FX",
    "phí": "FEE", "phí giao dịch": "FEE", "fee": "FEE",
    "thanh toán hóa đơn": "BILL_PAYMENT", "thanh toán": "BILL_PAYMENT",
    "nạp tiền": "DEPOSIT", "rút tiền": "WITHDRAWAL",
    "nạp": "DEPOSIT", "rút": "WITHDRAWAL",
}

# ── Status ───────────────────────────────────────────────────────────────────
_BK_STATUS_MAP: Dict[str, str] = {
    "thành công": "SUCCESS", "thành  công": "SUCCESS", "success": "SUCCESS",
    "hoàn thành": "SUCCESS", "đã xử lý": "SUCCESS",
    "thất bại": "FAILED", "lỗi": "FAILED", "failed": "FAILED", "bị lỗi": "FAILED",
    "đang xử lý": "PENDING", "chờ xử lý": "PENDING", "pending": "PENDING",
    "đã hủy": "CANCELLED", "bị hủy": "CANCELLED", "hủy": "CANCELLED",
}

# ── Currency ─────────────────────────────────────────────────────────────────
_BK_CURRENCY_MAP: Dict[str, str] = {
    "vnd": "VND", "việt nam đồng": "VND", "đồng": "VND",
    "usd": "USD", "đô la": "USD", "đô": "USD", "dollar": "USD",
    "eur": "EUR", "euro": "EUR",
    "jpy": "JPY", "yên": "JPY", "yen": "JPY",
    "cny": "CNY", "nhân dân tệ": "CNY", "tệ": "CNY",
    "gbp": "GBP", "bảng anh": "GBP",
}
_BK_CURRENCY_PATTERN = re.compile(
    r'(?:loại\s+tiền|tiền\s+tệ|ngoại\s+tệ|đơn\s+vị|currency)[:\s]+'
    r'(' + '|'.join(re.escape(k) for k in sorted(_BK_CURRENCY_MAP.keys(), key=len, reverse=True)) + r')'
    r'|\b(' + '|'.join(re.escape(k) for k in ["USD", "EUR", "JPY", "CNY", "GBP"]) + r')\b',
    re.IGNORECASE,
)

# ── Transaction ID ───────────────────────────────────────────────────────────
_BK_TRANS_ID = re.compile(
    r'(?:mã\s*(?:giao\s*dịch)?|trans(?:action)?\s*(?:id|ref)|số\s*giao\s*dịch)[:\s]*([A-Z0-9]{6,30})',
    re.IGNORECASE,
)

# ── Bank name ────────────────────────────────────────────────────────────────
_BK_BANK_NAMES = [
    "vietcombank", "vcb", "techcombank", "tcb", "vietinbank", "ctg",
    "bidv", "agribank", "mbbank", "mb", "acb", "sacombank", "stb",
    "vpbank", "tpbank", "hdbank", "shb", "eximbank", "ocb",
    "lienvietpostbank", "lpb", "msb", "vib", "seabank", "abbank",
    "bacabank", "baovietbank", "cbbank", "dongabank", "gpbank",
    "kienlongbank", "namabank", "ncb", "pgbank", "pvcombank",
    "saigonbank", "scb", "vietabank", "vietbank", "wooribank",
]
_BK_BANK_PATTERN = re.compile(
    r'(?:ngân\s*hàng|bank)\s+(\w+(?:\s+\w+){0,2})'
    r'|\b(' + '|'.join(re.escape(b) for b in sorted(_BK_BANK_NAMES, key=len, reverse=True)) + r')\b',
    re.IGNORECASE,
)

# ── Channel ──────────────────────────────────────────────────────────────────
_BK_CHANNEL_MAP: Dict[str, str] = {
    "internet banking": "INTERNET_BANKING", "ibanking": "INTERNET_BANKING",
    "mobile banking": "MOBILE_BANKING", "mbanking": "MOBILE_BANKING",
    "app": "MOBILE_BANKING",
    "atm": "ATM", "máy atm": "ATM",
    "quầy": "COUNTER", "quầy giao dịch": "COUNTER", "chi nhánh": "COUNTER",
    "pos": "POS", "máy pos": "POS",
    "sms banking": "SMS_BANKING", "sms": "SMS_BANKING",
}

# ── Recipient name ───────────────────────────────────────────────────────────
_BK_RECIPIENT_NAME = re.compile(
    r'(?:người\s*nhận|cho|gửi\s*(?:cho|đến|tới))\s+((?:'
    + _VIET_FAMILY_NAMES + r')(?:\s+[A-Za-zÀ-ỹ]+){1,3})',
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
    q_lower = question.lower()

    # ── 1. Recipient account (check before sender to avoid overlap) ──
    m = _BANKING_TO_ACCOUNT.search(question)
    if m:
        val = m.group(1) or m.group(2)
        entities.append({"to_account_no": val})

    # ── 2. Sender account: anchored first, bare long number fallback ──
    to_acct = m.group(1) or m.group(2) if m else None
    m = _BANKING_ACCOUNT_ANCHORED.search(question)
    if m and m.group(1) != to_acct:
        entities.append({"Số_tài_khoản": m.group(1)})
    elif not m:
        m2 = _BANKING_ACCOUNT_BARE.search(question)
        if m2 and m2.group(1) != to_acct:
            entities.append({"Số_tài_khoản": m2.group(1)})

    # ── 3. Date range ──
    start_date = end_date = None

    m = _BK_DATE_RANGE_ISO.search(question)
    if m:
        start_date, end_date = m.group(1), m.group(2)
    else:
        m = _BK_DATE_RANGE_DMY.search(question)
        if m:
            start_date = _parse_dmyslash(m.group(1))
            end_date = _parse_dmyslash(m.group(2))
        else:
            m = _BK_DATE_RANGE_WORDS.search(question)
            if m:
                today = datetime.date.today()
                y1 = m.group(3) or (m.group(6) if m.group(6) else str(today.year))
                y2 = m.group(6) or y1
                start_date = f"{y1}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
                end_date = f"{y2}-{m.group(5).zfill(2)}-{m.group(4).zfill(2)}"

    if start_date:
        entities.append({"from_date": start_date})
    if end_date:
        entities.append({"to_date": end_date})

    # ── 4. Relative / named period (only if no explicit range) ──
    if not start_date:
        today = datetime.date.today()
        m = _BK_RELATIVE_PERIOD.search(question)
        if m:
            n = int(m.group(1))
            unit = m.group(2).lower()
            if unit == "ngày":
                delta = datetime.timedelta(days=n)
            elif unit == "tuần":
                delta = datetime.timedelta(weeks=n)
            elif unit == "tháng":
                delta = datetime.timedelta(days=n * 30)
            else:  # năm
                delta = datetime.timedelta(days=n * 365)
            entities.append({"from_date": str(today - delta)})
            entities.append({"to_date": str(today)})
        else:
            period = _resolve_named_period(q_lower, today)
            if period:
                entities.append({"from_date": period[0]})
                entities.append({"to_date": period[1]})

    # ── 5. Single date (only if no range/period found) ──
    if not start_date and not any("from_date" in e for e in entities):
        single = _extract_single_date_banking(question)
        if single:
            entities.append({"from_date": single})
            entities.append({"to_date": single})

    # ── 6. Year-month / year-only (only if no date found yet) ──
    has_date = any(k in e for e in entities for k in ("from_date", "to_date"))
    if not has_date:
        m = _BK_YEARMONTH.search(question)
        if m:
            if m.group(1) and m.group(2):
                month, year = m.group(1).zfill(2), m.group(2)
            elif m.group(3):
                month = m.group(3).zfill(2)
                ym = _BK_YEAR_FALLBACK.search(question)
                year = ym.group(1) if ym else str(datetime.date.today().year)
            else:
                month, year = None, None
            if month and year:
                last_day = _last_day_of_month(int(year), int(month))
                entities.append({"from_date": f"{year}-{month}-01"})
                entities.append({"to_date": f"{year}-{month}-{last_day:02d}"})
        else:
            m = _BK_YEAR_ONLY.search(question)
            if m:
                y = m.group(1)
                entities.append({"from_date": f"{y}-01-01"})
                entities.append({"to_date": f"{y}-12-31"})

    # ── 7. Money amounts (range first, then single) ──
    m_range = _BANKING_MONEY_RANGE.search(question)
    if m_range:
        entities.append({"amount_min": _convert_money(m_range.group(1), m_range.group(2))})
        entities.append({"amount_max": _convert_money(m_range.group(3), m_range.group(4))})
    else:
        # "trên X triệu" → amount_min, "dưới X triệu" → amount_max
        q_lower_money = question.lower()
        money_matches = list(_BANKING_MONEY.finditer(question))
        for m in money_matches:
            val = _convert_money(m.group(1), m.group(2))
            # Check context before the number
            prefix = question[:m.start()].rstrip().lower()
            if prefix.endswith(("trên", "hơn", ">=", ">", "ít nhất", "tối thiểu")):
                entities.append({"amount_min": val})
            elif prefix.endswith(("dưới", "ít hơn", "<=", "<", "không quá", "tối đa")):
                entities.append({"amount_max": val})
            else:
                entities.append({"Số_tiền": val})

    # ── 8. Transaction type ──
    matched_type, matched_len = None, 0
    for phrase, type_val in _BK_TRANS_TYPE_MAP.items():
        if phrase in q_lower and len(phrase) > matched_len:
            matched_type, matched_len = type_val, len(phrase)
    if matched_type:
        entities.append({"Loại_giao_dịch": matched_type})

    # ── 9. Status ──
    matched_status, matched_len = None, 0
    for phrase, status_val in _BK_STATUS_MAP.items():
        if phrase in q_lower and len(phrase) > matched_len:
            matched_status, matched_len = status_val, len(phrase)
    if matched_status:
        entities.append({"status": matched_status})

    # ── 10. Currency ──
    m = _BK_CURRENCY_PATTERN.search(question)
    if m:
        raw = (m.group(1) or m.group(2)).strip().lower()
        entities.append({"Loại_tiền_tệ": _BK_CURRENCY_MAP.get(raw, raw.upper())})

    # ── 11. Transaction ID ──
    m = _BK_TRANS_ID.search(question)
    if m:
        entities.append({"số_giao_dịch": m.group(1)})

    # ── 12. Bank name ──
    m = _BK_BANK_PATTERN.search(question)
    if m:
        bank = (m.group(1) or m.group(2)).strip()
        entities.append({"bank": bank})

    # ── 13. Channel ──
    matched_ch, matched_len = None, 0
    for phrase, ch_val in _BK_CHANNEL_MAP.items():
        if phrase in q_lower and len(phrase) > matched_len:
            matched_ch, matched_len = ch_val, len(phrase)
    if matched_ch:
        entities.append({"kênh_giao_dịch": matched_ch})

    # ── 14. Recipient name ──
    m = _BK_RECIPIENT_NAME.search(question)
    if m:
        name = m.group(0)
        # Strip the prefix (người nhận / cho / gửi cho ...)
        name = re.sub(r'^(?:người\s*nhận|cho|gửi\s*(?:cho|đến|tới))\s+', '', name, flags=re.IGNORECASE).strip()
        if name:
            entities.append({"Tên_người_nhận": name})

    return entities


def _extract_single_date_banking(question: str) -> Optional[str]:
    """Extract a single date from banking question."""
    m = _BK_DATE_ISO.search(question)
    if m:
        return m.group(1)
    m = _BK_DATE_DMY.search(question)
    if m:
        return f"{m.group(3)}-{m.group(2).zfill(2)}-{m.group(1).zfill(2)}"
    m = _BK_DATE_WORDS.search(question)
    if m:
        d, mo = m.group(1).zfill(2), m.group(2).zfill(2)
        y = m.group(3) or str(datetime.date.today().year)
        return f"{y}-{mo}-{d}"
    return None


def _resolve_named_period(q_lower: str, today: datetime.date) -> Optional[tuple]:
    """Resolve Vietnamese named time period to (start_date, end_date) strings."""
    if "hôm nay" in q_lower:
        return str(today), str(today)
    if "hôm qua" in q_lower:
        d = today - datetime.timedelta(days=1)
        return str(d), str(d)

    # tuần này / tuần trước
    if "tuần này" in q_lower:
        start = today - datetime.timedelta(days=today.weekday())
        return str(start), str(today)
    if "tuần trước" in q_lower or "tuần qua" in q_lower:
        start = today - datetime.timedelta(days=today.weekday() + 7)
        end = start + datetime.timedelta(days=6)
        return str(start), str(end)

    # tháng này / tháng trước
    if "tháng này" in q_lower:
        start = today.replace(day=1)
        return str(start), str(today)
    if "tháng trước" in q_lower or "tháng qua" in q_lower or "tháng rồi" in q_lower:
        first = today.replace(day=1)
        last_month_end = first - datetime.timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        return str(last_month_start), str(last_month_end)

    # đầu tháng / cuối tháng
    if "đầu tháng" in q_lower:
        start = today.replace(day=1)
        end = min(today, start.replace(day=10))
        return str(start), str(end)
    if "cuối tháng" in q_lower:
        last_day = _last_day_of_month(today.year, today.month)
        start = today.replace(day=max(1, last_day - 9))
        return str(start), str(today.replace(day=last_day))

    # năm nay / năm ngoái
    if "năm nay" in q_lower:
        return f"{today.year}-01-01", str(today)
    if "năm ngoái" in q_lower or "năm trước" in q_lower or "năm qua" in q_lower:
        y = today.year - 1
        return f"{y}-01-01", f"{y}-12-31"

    # đầu năm / cuối năm
    if "đầu năm" in q_lower:
        return f"{today.year}-01-01", f"{today.year}-03-31"
    if "cuối năm" in q_lower:
        return f"{today.year}-10-01", f"{today.year}-12-31"

    # quý
    for q_str in ["quý 1", "quý i", "quý một", "q1"]:
        if q_str in q_lower:
            return f"{today.year}-01-01", f"{today.year}-03-31"
    for q_str in ["quý 2", "quý ii", "quý hai", "q2"]:
        if q_str in q_lower:
            return f"{today.year}-04-01", f"{today.year}-06-30"
    for q_str in ["quý 3", "quý iii", "quý ba", "q3"]:
        if q_str in q_lower:
            return f"{today.year}-07-01", f"{today.year}-09-30"
    for q_str in ["quý 4", "quý iv", "quý bốn", "q4"]:
        if q_str in q_lower:
            return f"{today.year}-10-01", f"{today.year}-12-31"
    if "quý này" in q_lower:
        q_num = (today.month - 1) // 3
        start_m = q_num * 3 + 1
        end_m = start_m + 2
        last_day = _last_day_of_month(today.year, end_m)
        return f"{today.year}-{start_m:02d}-01", f"{today.year}-{end_m:02d}-{last_day:02d}"
    if "quý trước" in q_lower or "quý qua" in q_lower:
        q_num = (today.month - 1) // 3 - 1
        y = today.year
        if q_num < 0:
            q_num = 3
            y -= 1
        start_m = q_num * 3 + 1
        end_m = start_m + 2
        last_day = _last_day_of_month(y, end_m)
        return f"{y}-{start_m:02d}-01", f"{y}-{end_m:02d}-{last_day:02d}"

    return None


def _last_day_of_month(year: int, month: int) -> int:
    """Return last day of the given month."""
    return calendar.monthrange(year, month)[1]


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
