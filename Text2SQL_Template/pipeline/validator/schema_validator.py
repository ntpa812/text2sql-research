"""
Validator – Schema Validator
Kiểm tra xem SQL có dùng đúng table/column trong schema không.
"""

import re
import logging
from typing import Dict, List, Tuple, Any

logger = logging.getLogger(__name__)


def validate_schema(
    sql: str,
    profiles: Dict[str, Any],
) -> Tuple[bool, str]:
    """
    Kiểm tra SQL chỉ dùng tables và columns tồn tại trong schema.
    Returns: (is_valid, error_message)
    """
    sql_upper = sql.upper()

    # Extract table names từ SQL (FROM, JOIN)
    used_tables = _extract_tables(sql)
    # Extract column names
    used_columns = _extract_columns(sql)

    # Build known tables & columns
    known_tables = set(t.lower() for t in profiles.keys())
    known_columns: Dict[str, set] = {}
    all_columns: set = set()
    for tname, profile in profiles.items():
        cols = set(c["name"].lower() for c in profile.get("columns", []))
        known_columns[tname.lower()] = cols
        all_columns.update(cols)

    # Validate tables
    invalid_tables = []
    for t in used_tables:
        if t.lower() not in known_tables:
            invalid_tables.append(t)

    if invalid_tables:
        return False, f"Unknown tables: {', '.join(invalid_tables)}. Available: {', '.join(known_tables)}"

    # Validate columns (against all known columns, because JOINs mix tables)
    invalid_columns = []
    for c in used_columns:
        if c.lower() not in all_columns:
            # Skip SQL functions / aliases / numbers
            if c.upper() in (
                "COUNT", "SUM", "AVG", "MAX", "MIN", "DISTINCT", "AS", "ASC", "DESC", "NULL", "LIMIT",
                "CAST", "COALESCE", "IFNULL", "LENGTH", "LOWER", "UPPER", "TRIM", "REPLACE", "SUBSTR",
                "DATE", "DATETIME", "STRFTIME", "JULIANDAY", "ROUND", "ABS", "TOTAL", "GROUP_CONCAT",
                "DATE_FORMAT", "MONTH", "YEAR", "DAY", "CURDATE", "NOW", "EXTRACT",
                "INTEGER", "TEXT", "REAL", "CASE", "WHEN", "THEN", "ELSE", "END",
            ):
                continue
            if c.isdigit():
                continue
            invalid_columns.append(c)

    if invalid_columns:
        return False, f"Unknown columns: {', '.join(invalid_columns)}"

    return True, ""


def _extract_tables(sql: str) -> List[str]:
    """Extract table names từ FROM / JOIN clauses."""
    tables = []

    # FROM table_name
    from_pattern = re.findall(r'\bFROM\s+(\w+)', sql, re.IGNORECASE)
    tables.extend(from_pattern)

    # JOIN table_name
    join_pattern = re.findall(r'\bJOIN\s+(\w+)', sql, re.IGNORECASE)
    tables.extend(join_pattern)

    return list(set(tables))


def _extract_columns(sql: str) -> List[str]:
    """Extract column names used in SQL."""
    columns = []

    # WHERE col = value, AND col LIKE, AND col BETWEEN
    where_pattern = re.findall(r'(?:WHERE|AND|OR)\s+(\w+)\s*(?:=|!=|<>|>=|<=|>|<|LIKE|BETWEEN|IN|IS)', sql, re.IGNORECASE)
    columns.extend(where_pattern)

    # ORDER BY col
    order_pattern = re.findall(r'ORDER\s+BY\s+([\w,\s]+?)(?:\s+ASC|\s+DESC|\s*;|\s*$|\s+LIMIT)', sql, re.IGNORECASE)
    for match in order_pattern:
        for col in match.split(','):
            col = col.strip().split()[0] if col.strip() else ""
            if col:
                columns.append(col)

    # SELECT col1, col2 (not *)
    select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
    if select_match:
        select_part = select_match.group(1).strip()
        if select_part != "*":
            for part in select_part.split(','):
                part = part.strip()
                # Skip "expr AS alias" — only validate the source column, not alias
                if re.search(r'\bAS\s+\w+', part, re.IGNORECASE):
                    # Extract column before AS, skip function calls
                    source = re.split(r'\bAS\b', part, flags=re.IGNORECASE)[0].strip()
                    col_match = re.match(r'(?:\w+\.)?([\w]+)', source)
                else:
                    col_match = re.match(r'(?:\w+\.)?([\w]+)', part)
                if col_match:
                    columns.append(col_match.group(1))

    return list(set(columns))
