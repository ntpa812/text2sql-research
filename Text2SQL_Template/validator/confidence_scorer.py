"""
Validator – Confidence Scorer
Chấm điểm confidence cho kết quả pipeline.

Scoring table:
  SQL chạy được       +0.4
  Entity hợp lệ       +0.3
  Column đúng schema   +0.2
  row > 0              +0.1
  Semantic check pass  +0.1 (bonus giảm từ entity nếu có)

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
) -> Dict[str, Any]:
    """
    Tính confidence score cho pipeline result.

    Returns: {
        "score": float,
        "passed": bool,
        "breakdown": { component: score },
    }
    """
    breakdown: Dict[str, float] = {}

    # SQL chạy được (không syntax/runtime error)
    breakdown["sql_executable"] = 0.4 if sql_executed else 0.0

    # Entity hợp lệ (tồn tại trong DB, enum đúng)
    breakdown["entity_valid"] = 0.25 if entity_valid else 0.0

    # Column đúng schema
    breakdown["schema_valid"] = 0.2 if schema_valid else 0.0

    # Có kết quả
    breakdown["has_rows"] = 0.1 if row_count > 0 else 0.0

    # Semantic check
    breakdown["semantic_ok"] = 0.05 if semantic_ok else 0.0

    score = round(sum(breakdown.values()), 2)
    passed = score >= THRESHOLD_PASS

    logger.info(f"[Confidence] score={score} passed={passed} breakdown={breakdown}")

    return {
        "score": score,
        "passed": passed,
        "threshold": THRESHOLD_PASS,
        "breakdown": breakdown,
    }
