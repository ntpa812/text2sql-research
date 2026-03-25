"""
Entity Extraction – NER Fallback LLM
Khi local NER fail hoặc confidence thấp, dùng LLM để extract entities.
"""

import json
import logging
from typing import Dict, FrozenSet, Optional

logger = logging.getLogger(__name__)

# ── Valid entity keys per domain (filter out LLM hallucinations) ──────────────
_VALID_KEYS_BANKING: FrozenSet[str] = frozenset({
    "account_no", "to_account_no", "recipient_name",
    "start_date", "end_date", "amount", "amount_min", "amount_max",
    "transaction_type", "status", "bank_name", "currency",
    "trans_id", "channel",
})

_VALID_KEYS_HRM: FrozenSet[str] = frozenset({
    "employee_id", "employee_name", "department_name", "employment_status",
    "start_date", "end_date", "attendance_date", "year_month", "year_only",
    "gender", "salary_min", "salary_max",
})

# ── Domain-specific prompts ───────────────────────────────────────────────────
_PROMPT_BANKING = """You are an entity extractor for a Vietnamese banking chatbot.

Extract the following entities from the user question if present:
- account_no: bank account number (digits only)
- to_account_no: recipient account number
- recipient_name: name of the recipient
- start_date: start date (YYYY-MM-DD)
- end_date: end date (YYYY-MM-DD)
- amount: money amount (number only)
- amount_min: minimum amount filter
- amount_max: maximum amount filter
- transaction_type: TRANSFER | SAVING | LOAN | FX | FEE | BILL_PAYMENT
- status: SUCCESS | FAILED | PENDING | PROCESSING | REJECTED | CANCELLED
- bank_name: bank name
- currency: currency code (VND, USD, ...)
- trans_id: transaction ID
- channel: transaction channel

User question: {question}

Return ONLY a valid JSON object with found entities. If an entity is not found, do not include it.
Example: {{"account_no": "123456789", "start_date": "2026-01-01"}}"""

_PROMPT_HRM = """You are an entity extractor for a Vietnamese HRM (Human Resource Management) chatbot.

Extract the following entities from the user question if present:
- employee_id: employee ID code (e.g. EMP001)
- employee_name: full name of employee in Vietnamese
- department_name: department name in Vietnamese
- employment_status: ACTIVE | PROBATION | RESIGNED | SUSPENDED
- start_date: start date filter (YYYY-MM-DD)
- end_date: end date filter (YYYY-MM-DD)
- attendance_date: specific attendance date (YYYY-MM-DD)
- year_month: month filter in YYYY-MM format (e.g. 2026-03)
- year_only: year filter as 4-digit string (e.g. 2026)
- gender: MALE | FEMALE
- salary_min: minimum salary as integer (VND)
- salary_max: maximum salary as integer (VND)

User question: {question}

Return ONLY a valid JSON object with found entities. If an entity is not found, do not include it.
Example: {{"department_name": "kinh doanh", "employment_status": "ACTIVE"}}"""


# ── Public API ────────────────────────────────────────────────────────────────

def extract_entities_llm(
    question: str,
    llm_generate_fn=None,
    domain_id: Optional[str] = None,
) -> Dict[str, str]:
    """
    Extract entities bằng LLM.

    Args:
        question:         Câu hỏi tiếng Việt của người dùng.
        llm_generate_fn:  Callable nhận prompt string, trả về response string.
        domain_id:        ``"banking"`` | ``"hrm"`` — xác định prompt và valid keys.

    Returns:
        Dict entity đã validate theo domain schema.
    """
    if llm_generate_fn is None:
        logger.warning("[NER-LLM] No LLM generate function provided.")
        return {}

    prompt_tmpl = _PROMPT_HRM if domain_id == "hrm" else _PROMPT_BANKING
    prompt = prompt_tmpl.format(question=question)

    try:
        response = llm_generate_fn(prompt)
        raw = _parse_json_response(response)
        entities = _validate_keys(raw, domain_id)
        logger.info(f"[NER-LLM] domain={domain_id} extracted={entities}")
        return entities
    except Exception as e:
        logger.error(f"[NER-LLM] Failed: {e}")
        return {}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _parse_json_response(response: str) -> Dict:
    """Parse JSON từ LLM response, xử lý trường hợp có text thừa."""
    response = response.strip()
    start = response.find("{")
    end = response.rfind("}") + 1
    if start != -1 and end > start:
        return json.loads(response[start:end])
    return {}


def _validate_keys(raw: Dict, domain_id: Optional[str]) -> Dict[str, str]:
    """Filter ra chỉ giữ lại các keys hợp lệ theo domain schema."""
    valid = _VALID_KEYS_HRM if domain_id == "hrm" else _VALID_KEYS_BANKING
    result: Dict[str, str] = {}
    for k, v in raw.items():
        if k in valid:
            if v is not None and str(v).strip():
                result[k] = str(v).strip()
        else:
            logger.debug(f"[NER-LLM] Ignoring unknown entity key: '{k}'")
    return result
