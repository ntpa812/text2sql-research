"""
Pipeline – Test Mock
Inject mock account vào SQL khi chạy test offline.
Thay thế runtime placeholder bằng test account.
"""

import re
import logging
from typing import Dict

from config.settings import TEST_MODE, TEST_ACCOUNT, TEST_CUSTOMER_ID

logger = logging.getLogger(__name__)

# Placeholder patterns → replacement values
_PLACEHOLDERS: Dict[str, str] = {
    "{current_user_account}": TEST_ACCOUNT,
    "{account_number}": TEST_ACCOUNT,
    "{account_no}": TEST_ACCOUNT,
    "{customer_id}": TEST_CUSTOMER_ID,
    "{user_id}": TEST_CUSTOMER_ID,
}


def inject_test_account(sql: str) -> str:
    """
    Inject mock account khi TEST_MODE=True.
    Thay thế placeholder trong SQL bằng test values.
    """
    if not TEST_MODE:
        return sql

    original = sql
    for placeholder, value in _PLACEHOLDERS.items():
        sql = sql.replace(placeholder, f"'{value}'")

    if sql != original:
        logger.info(f"[TestMock] Injected test account: {TEST_ACCOUNT}")

    return sql


def inject_test_entities(entities: Dict[str, str]) -> Dict[str, str]:
    """
    Inject mock entities khi TEST_MODE=True.
    Nếu entity account_no/customer_id trống → fill test value.
    """
    if not TEST_MODE:
        return entities

    result = dict(entities)

    if "account_no" not in result or not result["account_no"]:
        result["account_no"] = TEST_ACCOUNT
        logger.info(f"[TestMock] Injected test account_no: {TEST_ACCOUNT}")

    return result
