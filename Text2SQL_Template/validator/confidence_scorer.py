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

THRESHOLD_PASS = 0.6


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
    breakdown["sql_executable"] = 0.3 if sql_executed else 0.0

    # Structure score (table, column, WHERE, operators)
    breakdown["structure"] = round(min(structure_score, 1.0) * 0.3, 3)

    # Entity hợp lệ (tồn tại trong DB, enum đúng)
    breakdown["entity_valid"] = 0.2 if entity_valid else 0.0

    # Semantic check
    breakdown["semantic_ok"] = 0.1 if semantic_ok else 0.0

    # Có kết quả (bonus, KHÔNG phải tiêu chí chính)
    breakdown["has_rows"] = 0.1 if row_count > 0 else 0.0

    score = round(sum(breakdown.values()), 2)
    passed = score >= THRESHOLD_PASS

    logger.info(f"[Confidence] score={score} passed={passed} breakdown={breakdown}")

    return {
        "score": score,
        "passed": passed,
        "threshold": THRESHOLD_PASS,
        "breakdown": breakdown,
    }
