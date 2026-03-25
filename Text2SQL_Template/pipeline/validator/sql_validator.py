"""
Validator – SQL Validator
Kiểm tra cú pháp SQL.
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)


def validate_syntax(sql: str) -> Tuple[bool, str]:
    """
    Kiểm tra SQL syntax bằng sqlparse.
    Returns: (is_valid, error_message)
    """
    if not sql or not sql.strip():
        return False, "Empty SQL query"

    sql = sql.strip()

    # Basic check: phải bắt đầu bằng SELECT
    if not sql.upper().lstrip().startswith("SELECT"):
        return False, "SQL must start with SELECT"

    try:
        import sqlparse
        
        parsed = sqlparse.parse(sql)
        if not parsed:
            return False, "Failed to parse SQL"

        stmt = parsed[0]
        if stmt.get_type() != "SELECT":
            return False, f"Expected SELECT, got {stmt.get_type()}"

        # Check balanced parentheses
        open_count = sql.count('(')
        close_count = sql.count(')')
        if open_count != close_count:
            return False, f"Unbalanced parentheses: {open_count} open, {close_count} close"

        return True, ""

    except ImportError:
        # sqlparse not available, do basic checks
        logger.warning("[Validator] sqlparse not installed, using basic validation")
        return _basic_syntax_check(sql)
    except Exception as e:
        return False, f"Parse error: {str(e)}"


def _basic_syntax_check(sql: str) -> Tuple[bool, str]:
    """Basic SQL syntax check without sqlparse."""
    sql_upper = sql.upper().strip()

    if not sql_upper.startswith("SELECT"):
        return False, "Must start with SELECT"

    if "FROM" not in sql_upper:
        return False, "Missing FROM clause"

    open_count = sql.count('(')
    close_count = sql.count(')')
    if open_count != close_count:
        return False, f"Unbalanced parentheses"

    # Check for unclosed quotes
    single_quotes = sql.count("'")
    if single_quotes % 2 != 0:
        return False, "Unclosed single quote"

    return True, ""
