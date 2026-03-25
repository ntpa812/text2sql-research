"""
SQL Generation – SQL Repairer
Repair invalid SQL queries thay vì regenerate.
Áp dụng các rules để fix lỗi phổ biến.
"""

import re
import logging
from typing import Tuple, List

logger = logging.getLogger(__name__)


def repair_sql(
    sql: str,
    error_msg: str = "",
    question: str = "",
    entities: dict = None,
) -> Tuple[bool, str]:
    """
    Cố gắng repair SQL bị lỗi.
    Returns: (success, repaired_sql)
    
    Repair strategies:
    1. Fix missing FROM clause
    2. Fix missing WHERE conditions
    3. Fix column reference errors
    4. Fix time filter issues
    5. Fix aggregation without GROUP BY
    """
    if not sql or not sql.strip():
        return False, ""
    
    entities = entities or {}
    error_lower = error_msg.lower()
    sql_lower = sql.lower()
    
    # Attempt repairs in order
    repairs = [
        ("missing_from", _repair_missing_from),
        ("missing_where", _repair_missing_where),
        ("column_not_found", _repair_column_reference),
        ("time_filter", _repair_time_filter),
        ("aggregation", _repair_aggregation),
        ("syntax", _repair_syntax),
    ]
    
    for repair_type, repair_fn in repairs:
        if _should_apply_repair(repair_type, error_lower, sql_lower, question):
            try:
                repaired = repair_fn(sql, error_msg, question, entities)
                if repaired and repaired != sql:
                    logger.info(f"[SQLRepairer] Applied repair: {repair_type}")
                    logger.debug(f"[SQLRepairer] Original: {sql[:100]}...")
                    logger.debug(f"[SQLRepairer] Repaired: {repaired[:100]}...")
                    return True, repaired
            except Exception as e:
                logger.warning(f"[SQLRepairer] Repair {repair_type} failed: {e}")
                continue
    
    return False, sql


def _should_apply_repair(repair_type: str, error: str, sql: str, question: str) -> bool:
    """Quyết định có nên áp dụng repair này không."""
    rules = {
        "missing_from": "from" not in sql or "unknown table" in error,
        "missing_where": "where" not in sql and any(kw in question.lower() for kw in ["tài khoản", "account", "số tiền", "amount", "ngày", "date"]),
        "column_not_found": "unknown column" in error or "not found" in error,
        "time_filter": "time" in question.lower() and "where" not in sql,
        "aggregation": "group by" not in sql and any(kw in sql for kw in ["sum(", "count(", "avg(", "max(", "min("]),
        "syntax": "syntax" in error or "unexpected" in error,
    }
    return rules.get(repair_type, False)


def _repair_missing_from(sql: str, error: str, question: str, entities: dict) -> str:
    """Repair: Thêm FROM clause nếu thiếu."""
    if "from" in sql.lower():
        return sql
    
    # Detect main table từ question/entities
    table_map = {
        "giao dịch": "transaction",
        "tài khoản": "customer_account",
        "khách hàng": "customer",
        "account": "customer_account",
        "transaction": "transaction",
        "customer": "customer",
    }
    
    main_table = None
    for keyword, table in table_map.items():
        if keyword in question.lower():
            main_table = table
            break
    
    if not main_table:
        main_table = "transaction"
    
    # Insert FROM clause before WHERE
    where_match = re.search(r'\bWHERE\b', sql, re.IGNORECASE)
    if where_match:
        insert_pos = where_match.start()
        return f"{sql[:insert_pos]} FROM {main_table} {sql[insert_pos:]}"
    
    # Append FROM at end
    return f"{sql} FROM {main_table}"


def _repair_missing_where(sql: str, error: str, question: str, entities: dict) -> str:
    """Repair: Thêm WHERE clause nếu thiếu khi có entities."""
    if "where" in sql.lower() or not entities:
        return sql
    
    # Build WHERE from entities
    where_conditions = []
    
    if "account_no" in entities:
        account = entities["account_no"]
        where_conditions.append(f"account_no = '{account}'")
    
    if "amount" in entities:
        amount = entities["amount"]
        # amount có thể là threshold hoặc exact value
        if "trên" in question or "larger than" in question:
            where_conditions.append(f"amount_transfer >= {amount}")
        elif "dưới" in question or "less than" in question:
            where_conditions.append(f"amount_transfer <= {amount}")
        else:
            where_conditions.append(f"amount_transfer = {amount}")
    
    if not where_conditions:
        return sql
    
    where_clause = " AND ".join(where_conditions)
    
    # Append WHERE
    if sql.rstrip().endswith(";"):
        sql = sql.rstrip()[:-1]
    
    return f"{sql} WHERE {where_clause};"


def _repair_column_reference(sql: str, error: str, question: str, entities: dict) -> str:
    """Repair: Fix column reference errors."""
    # Try to extract missing column from error
    col_match = re.search(r"column.*['\"]?(\w+)['\"]?", error, re.IGNORECASE)
    if not col_match:
        return sql
    
    missing_col = col_match.group(1)
    logger.debug(f"[SQLRepairer] Trying to fix column: {missing_col}")
    
    # Common column mappings
    col_map = {
        "trans_time": "t.trans_time",
        "account_no": "c.account_no",
        "amount": "amount_transfer",
        "status": "trans_status",
        "type": "trans_type",
    }
    
    # Replace unqualified column with qualified
    if missing_col in col_map:
        replacement = col_map[missing_col]
        sql_fixed = re.sub(
            rf'\b{missing_col}\b',
            replacement,
            sql,
            flags=re.IGNORECASE
        )
        return sql_fixed
    
    return sql


def _repair_time_filter(sql: str, error: str, question: str, entities: dict) -> str:
    """Repair: Thêm time filter nếu question có time keywords."""
    has_time_kw = any(kw in question.lower() for kw in [
        "tuần", "tháng", "quý", "năm", "hôm nay", "hôm qua", "ngày",
        "week", "month", "quarter", "year", "today", "yesterday", "day"
    ])
    
    if not has_time_kw or "trans_time" in sql.lower():
        return sql
    
    # Infer time filter from question
    time_filter = ""
    
    if "tuần" in question.lower() or "week" in question.lower():
        time_filter = "AND t.trans_time >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)"
    elif "tháng" in question.lower() or "month" in question.lower():
        time_filter = "AND YEAR(t.trans_time) = YEAR(NOW()) AND MONTH(t.trans_time) = MONTH(NOW())"
    elif "quý" in question.lower() or "quarter" in question.lower():
        time_filter = "AND QUARTER(t.trans_time) = QUARTER(NOW())"
    elif "năm" in question.lower() or "year" in question.lower():
        time_filter = "AND YEAR(t.trans_time) = YEAR(NOW())"
    elif "hôm" in question.lower() or "today" in question.lower():
        time_filter = "AND DATE(t.trans_time) = CURDATE()"
    
    if not time_filter:
        return sql
    
    # Insert before LIMIT or at end
    limit_match = re.search(r'\bLIMIT\b', sql, re.IGNORECASE)
    if limit_match:
        insert_pos = limit_match.start()
        return f"{sql[:insert_pos]} {time_filter} {sql[insert_pos:]}"
    
    # Insert before ;
    sql = sql.rstrip()
    if sql.endswith(";"):
        return f"{sql[:-1]} {time_filter};"
    
    return f"{sql} {time_filter}"


def _repair_aggregation(sql: str, error: str, question: str, entities: dict) -> str:
    """Repair: Thêm GROUP BY khi cần aggregation."""
    has_agg = any(agg in sql.upper() for agg in ["SUM(", "COUNT(", "AVG(", "MAX(", "MIN("])
    
    if not has_agg or "group by" in sql.lower():
        return sql
    
    # Check if SELECT has non-aggregated columns
    select_match = re.search(r'SELECT\s+(.+?)\s+FROM', sql, re.IGNORECASE | re.DOTALL)
    if not select_match:
        return sql
    
    select_clause = select_match.group(1)
    
    # Find non-aggregated columns
    non_agg_cols = re.findall(r'\b(\w+)\b(?!\s*\()', select_clause)
    non_agg_cols = [c for c in non_agg_cols if c.upper() not in ["DISTINCT", "AS"]]
    
    if not non_agg_cols:
        return sql
    
    # Add GROUP BY
    from_match = re.search(r'\bFROM\b', sql, re.IGNORECASE)
    where_match = re.search(r'\bWHERE\b', sql, re.IGNORECASE)
    limit_match = re.search(r'\bLIMIT\b', sql, re.IGNORECASE)
    
    insert_pos = None
    if limit_match:
        insert_pos = limit_match.start()
    elif where_match:
        # Find end of WHERE clause
        insert_pos = where_match.end()
        # Move to end of last condition
        next_keyword = re.search(r'\b(LIMIT|ORDER|GROUP|HAVING)\b', sql[insert_pos:], re.IGNORECASE)
        if next_keyword:
            insert_pos += next_keyword.start()
        else:
            # Find semicolon
            semi = sql.find(";", insert_pos)
            insert_pos = semi if semi > 0 else len(sql)
    
    if insert_pos is None:
        return sql
    
    group_cols = ", ".join(non_agg_cols[:2])  # Limit to 2 columns
    group_clause = f" GROUP BY {group_cols}"
    
    return f"{sql[:insert_pos]} {group_clause} {sql[insert_pos:]}"


def _repair_syntax(sql: str, error: str, question: str, entities: dict) -> str:
    """Repair: Fix common SQL syntax errors."""
    repairs = [
        # Missing comma in SELECT
        (r'SELECT\s+(\w+)\s+(\w+)\s+FROM', r'SELECT \1, \2 FROM'),
        # Single quote in string
        (r"'\s*'", r"''"),
        # Missing parenthesis
        (r'COUNT\s+\*', r'COUNT(*)'),
        (r'SUM\s+\((\w+)\)', r'SUM(\1)'),
    ]
    
    repaired = sql
    for pattern, replacement in repairs:
        repaired = re.sub(pattern, replacement, repaired, flags=re.IGNORECASE)
    
    return repaired
