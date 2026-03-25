"""
Entity Extraction – NER Fallback LLM
Khi local NER fail, dùng LLM để extract entities.
"""

import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

ENTITY_EXTRACTION_PROMPT = """You are an entity extractor for a Vietnamese banking chatbot.

Extract the following entities from the user question if present:
- account_no: bank account number (digits only)
- to_account_no: recipient account number
- recipient_name: name of the recipient
- start_date: start date (YYYY-MM-DD)
- end_date: end date (YYYY-MM-DD)
- amount: money amount (number only)
- amount_min: minimum amount filter
- amount_max: maximum amount filter
- transaction_type: TRANSFER, SAVING, LOAN, FX, FEE, BILL_PAYMENT
- status: transaction status
- bank_name: bank name
- currency: currency code
- trans_id: transaction ID
- channel: transaction channel

User question: {question}

Return ONLY a valid JSON object with found entities. If an entity is not found, do not include it.
Example: {{"account_no": "123456789", "start_date": "2026-01-01"}}
"""


def extract_entities_llm(
    question: str,
    llm_generate_fn=None,
) -> Dict[str, str]:
    """
    Extract entities bằng LLM.
    llm_generate_fn: callable nhận prompt string, trả về response string.
    """
    if llm_generate_fn is None:
        logger.warning("[NER-LLM] No LLM generate function provided.")
        return {}

    prompt = ENTITY_EXTRACTION_PROMPT.format(question=question)

    try:
        response = llm_generate_fn(prompt)
        entities = _parse_json_response(response)
        logger.info(f"[NER-LLM] Extracted: {entities}")
        return entities
    except Exception as e:
        logger.error(f"[NER-LLM] Failed: {e}")
        return {}


def _parse_json_response(response: str) -> Dict[str, str]:
    """Parse JSON từ LLM response, xử lý trường hợp response có text thừa."""
    response = response.strip()

    # Tìm JSON object trong response
    start = response.find("{")
    end = response.rfind("}") + 1
    if start != -1 and end > start:
        json_str = response[start:end]
        return json.loads(json_str)

    return {}
