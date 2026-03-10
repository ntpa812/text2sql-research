"""
Slot Filling – Slot Filler
Fill entities vào SQL template bằng parameterized binding (an toàn).
"""

import re
import logging
from typing import Dict, Optional, List, Tuple

logger = logging.getLogger(__name__)

# Placeholder pattern trong template: {entity_name}
PLACEHOLDER_PATTERN = re.compile(r'\{(\w+)\}')


def fill_template(
    template_sql: str,
    entities: Dict[str, str],
) -> Tuple[str, Dict[str, str]]:
    """
    Fill entities vào SQL template.
    Trả về (filled_sql, unfilled_slots).

    QUAN TRỌNG: Dùng string replacement cho template hint,
    SQL thực tế sẽ dùng parameterized query trong executor.
    """
    unfilled: Dict[str, str] = {}
    filled_sql = template_sql

    placeholders = PLACEHOLDER_PATTERN.findall(template_sql)
    logger.info(f"[Slot] Template placeholders: {placeholders}")
    logger.info(f"[Slot] Available entities: {list(entities.keys())}")

    for placeholder in placeholders:
        value = _find_entity_value(placeholder, entities)
        if value is not None:
            filled_sql = filled_sql.replace(f"{{{placeholder}}}", value)
        else:
            unfilled[placeholder] = f"Missing entity: {placeholder}"

    if unfilled:
        logger.warning(f"[Slot] Unfilled slots: {list(unfilled.keys())}")

    return filled_sql, unfilled


def _find_entity_value(placeholder: str, entities: Dict[str, str]) -> Optional[str]:
    """
    Tìm entity value cho placeholder.
    Hỗ trợ mapping aliases: account_number → account_no, etc.
    """
    # Direct match
    if placeholder in entities:
        return entities[placeholder]

    # Alias mapping
    aliases = {
        "account_number": ["account_no", "from_account_no"],
        "to_account_number": ["to_account_no"],
        "min_amount": ["amount_min", "amount"],
        "max_amount": ["amount_max", "amount"],
        "status": ["trans_status"],
        "recipient_name": ["to_account_fullname"],
    }

    for alias_key, alias_values in aliases.items():
        if placeholder == alias_key:
            for av in alias_values:
                if av in entities:
                    return entities[av]
        if placeholder in alias_values:
            if alias_key in entities:
                return entities[alias_key]

    return None


def get_parameterized_query(
    sql: str,
    entities: Dict[str, str],
) -> Tuple[str, List[str]]:
    """
    Convert SQL với giá trị literal → parameterized query.
    Thay thế string literals đã biết bằng %s placeholder.
    Returns: (parameterized_sql, param_values)
    """
    params: List[str] = []
    param_sql = sql

    for key, value in entities.items():
        if f"'{value}'" in param_sql:
            param_sql = param_sql.replace(f"'{value}'", "%s", 1)
            params.append(value)

    return param_sql, params
