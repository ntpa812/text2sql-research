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
    Chạy tất cả 3 validators (pre-execution).
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


def classify_execution_error(error_msg: str) -> str:
    """
    Phân loại lỗi DB execution thành 3 nhóm:
    - "syntax": column does not exist, syntax error near ...
    - "runtime": division by zero, invalid cast, timeout
    - "connection": connection refused, access denied
    """
    err = error_msg.lower()

    syntax_indicators = [
        "syntax error", "unknown column", "does not exist",
        "no such column", "ambiguous column", "you have an error in your sql",
        "near \"", "at line", "unrecognized token",
    ]
    for indicator in syntax_indicators:
        if indicator in err:
            return "syntax"

    runtime_indicators = [
        "division by zero", "divide by zero", "invalid cast",
        "data truncated", "out of range", "incorrect",
        "deadlock", "lock wait timeout",
    ]
    for indicator in runtime_indicators:
        if indicator in err:
            return "runtime"

    connection_indicators = [
        "connection refused", "access denied", "not installed",
        "can't connect", "lost connection", "gone away",
    ]
    for indicator in connection_indicators:
        if indicator in err:
            return "connection"

    return "runtime"
