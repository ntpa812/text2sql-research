"""
Pipeline – Retry Handler
Quản lý retry strategy cho SQL generation.

Logic:
  Attempt 1: Try SQL repair (fix lỗi syntax/schema không regenerate)
  Attempt 2: If repair failed → regenerate full SQL từ LLM
  connection/security errors → không retry
"""

import logging
from typing import Dict, Any, Optional, Tuple, Callable

from sql_generation.sql_prompt_builder import build_retry_prompt
from sql_generation.sql_repairer import repair_sql

logger = logging.getLogger(__name__)


class RetryHandler:
    """
    Smart retry handler với SQL repair strategy:
    - Attempt 1: Try SQL repair (fix syntax/schema without regenerate)
    - Attempt 2: If repair failed → regenerate from LLM
    - Max 2 retries total
    - Không retry connection errors
    """

    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries
        self.attempts: list = []
        self.repair_attempted_for: set = set()  # Track repair by error type

    def should_retry(self, error_type: str = "") -> bool:
        """Chỉ retry nếu lỗi có thể sửa được."""
        if error_type in ("connection", "security"):
            return False
        return len(self.attempts) < self.max_retries
    
    def should_attempt_repair(self, error_type: str = "structure") -> bool:
        """Có nên thử repair SQL trước khi regenerate không.
        
        Return True if:
        - Repair not yet attempted for this error type
        - No recorded attempts yet (fresh error)
        """
        # Repair if: haven't tried repair for this error type AND no attempts recorded yet
        return error_type not in self.repair_attempted_for and len(self.attempts) == 0
    
    def should_regenerate(self) -> bool:
        """Có nên regenerate từ LLM không."""
        # Regenerate if: we have attempts to spare
        return len(self.attempts) < self.max_retries

    @property
    def repair_attempted(self) -> bool:
        """For backward compatibility - check if ANY repair was attempted."""
        return len(self.repair_attempted_for) > 0

    @property
    def retry_count(self) -> int:
        return len(self.attempts)

    def record_attempt(self, sql: str, error: str, error_type: str):
        self.attempts.append({
            "attempt": len(self.attempts) + 1,
            "sql": sql,
            "error": error,
            "error_type": error_type,
        })
    
    def attempt_repair(self, sql: str, error_msg: str = "", question: str = "", entities: dict = None, error_type: str = "structure") -> Tuple[bool, str]:
        """
        Cố gắng repair SQL bị lỗi.
        Args:
            sql: SQL query to repair
            error_msg: Error message
            question: User question
            entities: Extracted entities
            error_type: Type of error (structure, semantic, syntax, db_execution)
        Returns: (success, repaired_sql)
        """
        self.repair_attempted_for.add(error_type)
        success, repaired = repair_sql(sql, error_msg, question, entities)
        if success:
            logger.info(f"[Retry] SQL repair successful ({error_type})")
        else:
            logger.warning(f"[Retry] SQL repair failed ({error_type}), will regenerate")
        return success, repaired

    def get_retry_prompt(
        self,
        error_type: str,
        sql: str,
        error_message: str,
        schema: str = "",
        question: str = "",
        semantic_warnings: list = None,
    ) -> str:
        """
        Build retry prompt phù hợp với loại lỗi.
        """
        # Nếu có semantic warnings, thêm vào error message
        if semantic_warnings:
            extra = "\n\nSemantic issues:\n" + "\n".join(f"- {w}" for w in semantic_warnings)
            error_message = error_message + extra

        if error_type in ("syntax", "execution"):
            return build_retry_prompt("syntax", sql, error_message)
        elif error_type == "schema":
            return build_retry_prompt("schema", sql, error_message, schema=schema)
        elif error_type == "runtime":
            return build_retry_prompt("syntax", sql, error_message, schema=schema)
        elif error_type == "semantic":
            return build_retry_prompt("logic", sql, error_message, schema=schema, question=question)
        else:
            return build_retry_prompt("syntax", sql, error_message)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_attempts": len(self.attempts),
            "max_retries": self.max_retries,
            "attempts": self.attempts,
        }
