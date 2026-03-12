"""
Validator – Semantic Validator
Kiểm tra SQL có phù hợp ngữ nghĩa với câu hỏi không.
Rule-based: keyword matching giữa question → SQL structure.
"""

import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

# ─── Semantic rules: question keyword → expected SQL pattern ───
SEMANTIC_RULES: List[Tuple[str, str, str]] = [
    # (question_pattern, sql_must_contain, description)
    # Aggregation
    (r"tổng\b|tổng cộng|tổng số tiền", r"\bSUM\s*\(", "Câu hỏi yêu cầu tổng (SUM) nhưng SQL thiếu SUM()"),
    (r"trung bình|bình quân", r"\bAVG\s*\(", "Câu hỏi yêu cầu trung bình (AVG) nhưng SQL thiếu AVG()"),
    (r"bao nhiêu|số lượng|đếm|có mấy", r"\bCOUNT\s*\(", "Câu hỏi yêu cầu đếm (COUNT) nhưng SQL thiếu COUNT()"),
    (r"lớn nhất|cao nhất|max", r"\bMAX\s*\(", "Câu hỏi yêu cầu MAX nhưng SQL thiếu MAX()"),
    (r"nhỏ nhất|thấp nhất|min|ít nhất", r"\bMIN\s*\(", "Câu hỏi yêu cầu MIN nhưng SQL thiếu MIN()"),

    # Sorting
    (r"gần nhất|mới nhất|cuối cùng|gần đây", r"\bORDER\s+BY\b", "Câu hỏi yêu cầu sắp xếp nhưng SQL thiếu ORDER BY"),

    # Time filtering
    (r"hôm nay|hôm qua|tuần (này|trước|qua)|tháng (này|trước|qua)|năm nay",
     r"\bWHERE\b.*\b(trans_time|created_at|date)\b", "Câu hỏi có thời gian nhưng SQL thiếu filter thời gian"),
]


def validate_semantic(question: str, sql: str) -> Tuple[bool, List[str]]:
    """
    Kiểm tra ngữ nghĩa SQL có match câu hỏi.
    Returns: (is_valid, list_of_warnings)
    """
    if not question or not sql:
        return True, []

    warnings: List[str] = []
    question_lower = question.lower()
    sql_upper = sql.upper()

    for q_pattern, sql_pattern, description in SEMANTIC_RULES:
        # Câu hỏi match pattern?
        if re.search(q_pattern, question_lower):
            # SQL phải chứa pattern tương ứng
            if not re.search(sql_pattern, sql_upper, re.IGNORECASE):
                warnings.append(description)
                logger.warning(f"[Semantic] {description}")

    # Special: nếu SELECT * mà câu hỏi yêu cầu aggregation
    if re.search(r"tổng|trung bình|đếm|bao nhiêu|số lượng", question_lower):
        if re.search(r"SELECT\s+\*", sql_upper):
            warnings.append("Câu hỏi yêu cầu aggregation nhưng SQL dùng SELECT *")

    is_valid = len(warnings) == 0
    return is_valid, warnings
