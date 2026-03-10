"""
Validator – Security Guard
Cấm các SQL statements nguy hiểm: DROP, DELETE, UPDATE, INSERT, etc.
"""

import re
import logging
from typing import Tuple

from config.settings import BLOCKED_SQL_KEYWORDS

logger = logging.getLogger(__name__)


def validate_security(sql: str) -> Tuple[bool, str]:
    """
    Kiểm tra SQL không chứa keywords nguy hiểm.
    Returns: (is_valid, error_message)
    """
    sql_upper = sql.upper()

    for keyword in BLOCKED_SQL_KEYWORDS:
        # Match whole word to avoid false positives (e.g., "UPDATED_AT" column)
        pattern = r'\b' + re.escape(keyword) + r'\b'
        if re.search(pattern, sql_upper):
            msg = f"Blocked SQL keyword detected: {keyword}"
            logger.warning(f"[Security] {msg}")
            return False, msg

    # Check for multiple statements (SQL injection risk)
    # Strip trailing semicolon then check for remaining ones
    sql_cleaned = sql.strip().rstrip(';').strip()
    if ';' in sql_cleaned:
        msg = "Multiple SQL statements detected (possible injection)"
        logger.warning(f"[Security] {msg}")
        return False, msg

    # Check for comment-based injection attempts
    if '--' in sql or '/*' in sql:
        msg = "SQL comments detected (possible injection)"
        logger.warning(f"[Security] {msg}")
        return False, msg

    return True, ""


def validate_all(
    sql: str,
    profiles=None,
) -> Tuple[bool, str, str]:
    """
    Chạy tất cả 3 validators.
    Returns: (is_valid, error_message, error_type)
    error_type: "security" | "syntax" | "schema" | ""
    """
    from validator.sql_validator import validate_syntax
    from validator.schema_validator import validate_schema

    # 1. Security check FIRST
    is_valid, error = validate_security(sql)
    if not is_valid:
        return False, error, "security"

    # 2. Syntax check
    is_valid, error = validate_syntax(sql)
    if not is_valid:
        return False, error, "syntax"

    # 3. Schema check (if profiles provided)
    if profiles:
        is_valid, error = validate_schema(sql, profiles)
        if not is_valid:
            return False, error, "schema"

    return True, "", ""
