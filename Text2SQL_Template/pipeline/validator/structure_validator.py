"""
Validator – SQL Structure Validator
Kiểm tra SQL structure thay vì row count.
Validate: table đúng, column đúng, WHERE clause đúng, operators đúng.
Đây là tiêu chí chính thay cho row count.
"""

import re
import logging
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)


def validate_sql_structure(
    sql: str,
    question: str,
    entities: Dict[str, str],
    profiles: Dict[str, Any],
    intent: Dict[str, Any] = None,
) -> Tuple[bool, List[str], float]:
    """
    Kiểm tra SQL structure logic.
    Returns: (is_valid, issues, structure_score)
    
    structure_score: 0.0 - 1.0
      - table match:     0.25
      - column match:    0.25
      - WHERE clause:    0.25
      - operator/agg:    0.25
    """
    if not sql or not sql.strip():
        return False, ["Empty SQL"], 0.0

    issues: List[str] = []
    scores: Dict[str, float] = {}
    sql_upper = sql.upper()

    # ─── 1. Table validation ────────────────────────────────
    used_tables = _extract_tables(sql)
    known_tables = set(t.lower() for t in profiles.keys())

    if not used_tables:
        issues.append("SQL không có FROM clause")
        scores["table"] = 0.0
    else:
        invalid = [t for t in used_tables if t.lower() not in known_tables]
        if invalid:
            issues.append(f"Table không hợp lệ: {invalid}")
            scores["table"] = 0.0
        else:
            scores["table"] = 0.25

    # ─── 2. Column validation ───────────────────────────────
    used_columns = _extract_where_columns(sql)
    all_columns = set()
    for profile in profiles.values():
        for col in profile.get("columns", []):
            all_columns.add(col["name"].lower())

    if used_columns:
        invalid_cols = [c for c in used_columns if c.lower() not in all_columns
                        and c.upper() not in _SQL_FUNCTIONS]
        if invalid_cols:
            issues.append(f"Column không hợp lệ: {invalid_cols}")
            scores["column"] = 0.0
        else:
            scores["column"] = 0.25
    else:
        # SELECT * without WHERE is ok for simple queries
        scores["column"] = 0.15

    # ─── 3. WHERE clause validation ─────────────────────────
    has_where = "WHERE" in sql_upper
    needs_where = bool(entities)  # có entity → cần WHERE

    if needs_where and not has_where:
        issues.append("Có entities nhưng SQL thiếu WHERE clause")
        scores["where"] = 0.0
    elif has_where:
        # Check entity columns appear in WHERE
        where_score = _score_where_clause(sql, entities, profiles)
        scores["where"] = where_score
    else:
        scores["where"] = 0.25  # No entity, no WHERE → OK

    # ─── 4. Operator / Aggregation check ────────────────────
    agg_score = _score_operators(sql, question)
    scores["operator"] = agg_score

    total_score = round(sum(scores.values()), 2)
    is_valid = total_score >= 0.5 and len(issues) == 0

    logger.info(f"[StructureValidator] score={total_score} valid={is_valid} "
                f"scores={scores} issues={issues}")

    return is_valid, issues, total_score


# ─── Helper: extract tables ─────────────────────────────────

def _extract_tables(sql: str) -> List[str]:
    tables = []
    for match in re.finditer(r'\bFROM\s+(\w+)', sql, re.IGNORECASE):
        tables.append(match.group(1))
    for match in re.finditer(r'\bJOIN\s+(\w+)', sql, re.IGNORECASE):
        tables.append(match.group(1))
    return list(set(tables))


# ─── Helper: extract WHERE columns ──────────────────────────

def _extract_where_columns(sql: str) -> List[str]:
    """Extract column names used in WHERE / AND / OR / HAVING."""
    cols = []
    pattern = r'(?:WHERE|AND|OR|HAVING)\s+(?:\w+\.)?([\w]+)\s*(?:=|!=|<>|>=|<=|>|<|LIKE|BETWEEN|IN|IS)'
    for match in re.finditer(pattern, sql, re.IGNORECASE):
        cols.append(match.group(1))
    return list(set(cols))


# ─── Helper: score WHERE clause ─────────────────────────────

# Entity key → expected DB column name
ENTITY_COLUMN_MAP = {
    "account_no": ["account_no", "from_account_no", "to_account_no"],
    "to_account_no": ["to_account_no", "account_no"],
    "customer_id": ["customer_id", "core_customer_id", "cif_no"],
    "start_date": ["trans_time", "created_at", "updated_at"],
    "end_date": ["trans_time", "created_at", "updated_at"],
    "amount": ["amount", "total_amount"],
    "transaction_type": ["trans_code", "transaction_type"],
    "status": ["status", "trans_status"],
    "trans_id": ["trans_id", "reference_id"],
}


def _score_where_clause(
    sql: str,
    entities: Dict[str, str],
    profiles: Dict[str, Any],
) -> float:
    """Score WHERE clause: check entity → column mapping."""
    if not entities:
        return 0.25

    where_cols = _extract_where_columns(sql)
    where_cols_lower = [c.lower() for c in where_cols]

    matched = 0
    total = 0

    for entity_key in entities:
        expected_cols = ENTITY_COLUMN_MAP.get(entity_key, [])
        if not expected_cols:
            continue
        total += 1
        if any(ec in where_cols_lower for ec in expected_cols):
            matched += 1

    if total == 0:
        return 0.25

    ratio = matched / total
    return round(0.25 * ratio, 3)


# ─── Helper: score operators / aggregation ───────────────────

_SQL_FUNCTIONS = {"COUNT", "SUM", "AVG", "MAX", "MIN", "DISTINCT",
                  "COALESCE", "IFNULL", "NOW", "DATE", "YEAR", "MONTH"}

_AGG_KEYWORDS = {
    "tổng": "SUM", "tổng cộng": "SUM", "tổng số tiền": "SUM",
    "trung bình": "AVG", "bình quân": "AVG",
    "bao nhiêu": "COUNT", "số lượng": "COUNT", "đếm": "COUNT", "có mấy": "COUNT",
    "lớn nhất": "MAX", "cao nhất": "MAX",
    "nhỏ nhất": "MIN", "thấp nhất": "MIN", "ít nhất": "MIN",
}


def _score_operators(sql: str, question: str) -> float:
    """Check aggregation keywords in question vs SQL."""
    question_lower = question.lower()
    sql_upper = sql.upper()

    required_aggs = set()
    for keyword, func in _AGG_KEYWORDS.items():
        if keyword in question_lower:
            required_aggs.add(func)

    if not required_aggs:
        return 0.25  # No aggregation expected → pass

    found = 0
    for agg in required_aggs:
        if agg in sql_upper:
            found += 1

    if len(required_aggs) == 0:
        return 0.25

    ratio = found / len(required_aggs)
    return round(0.25 * ratio, 3)
