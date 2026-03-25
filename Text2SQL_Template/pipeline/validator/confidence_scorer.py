"""
Validator – Confidence Scorer
Chấm điểm confidence cho kết quả pipeline.

Scoring (structure-first, not row-count):
  SQL chạy được        +0.3
  Structure score       +0.3  (from structure_validator)
  Entity hợp lệ        +0.2
  Semantic check pass   +0.1
  row > 0               +0.1  (bonus, không phải tiêu chí chính)

Ngưỡng:
  score >= 0.6  → PASS
  score <  0.6  → RETRY / WARN
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

# ── Score thresholds ──────────────────────────────────────────────────────────
THRESHOLD_PASS = 0.6          # score >= này thì PASS

# ── Component weights (tổng = 1.0) ───────────────────────────────────────────
WEIGHT_SQL_EXECUTABLE = 0.3   # SQL chạy không lỗi syntax/runtime
WEIGHT_STRUCTURE      = 0.3   # Structure validator score (table, column, WHERE)
WEIGHT_ENTITY_VALID   = 0.2   # Entity tồn tại trong DB, enum đúng
WEIGHT_SEMANTIC_OK    = 0.1   # Semantic check pass
WEIGHT_HAS_ROWS       = 0.1   # Có ít nhất 1 dòng kết quả (bonus)


def compute_confidence(
    sql_executed: bool,
    entity_valid: bool,
    schema_valid: bool,
    row_count: int,
    semantic_ok: bool = True,
    structure_score: float = 0.0,
) -> Dict[str, Any]:
    """
    Tính confidence score cho pipeline result.
    Structure score là tiêu chí chính thay cho row count.

    Returns: {
        "score": float,
        "passed": bool,
        "breakdown": { component: score },
    }
    """
    breakdown: Dict[str, float] = {}

    # SQL chạy được (không syntax/runtime error)
    breakdown["sql_executable"] = WEIGHT_SQL_EXECUTABLE if sql_executed else 0.0

    # Structure score (table, column, WHERE, operators)
    breakdown["structure"] = round(min(structure_score, 1.0) * WEIGHT_STRUCTURE, 3)

    # Entity hợp lệ (tồn tại trong DB, enum đúng)
    breakdown["entity_valid"] = WEIGHT_ENTITY_VALID if entity_valid else 0.0

    # Semantic check
    breakdown["semantic_ok"] = WEIGHT_SEMANTIC_OK if semantic_ok else 0.0

    # Có kết quả (bonus, KHÔNG phải tiêu chí chính)
    breakdown["has_rows"] = WEIGHT_HAS_ROWS if row_count > 0 else 0.0

    score = round(sum(breakdown.values()), 2)
    passed = score >= THRESHOLD_PASS

    logger.info(f"[Confidence] score={score} passed={passed} breakdown={breakdown}")

    return {
        "score": score,
        "passed": passed,
        "threshold": THRESHOLD_PASS,
        "breakdown": breakdown,
    }
