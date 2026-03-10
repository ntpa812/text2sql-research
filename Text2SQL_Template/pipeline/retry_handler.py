"""
Pipeline – Retry Handler
Quản lý retry strategy cho SQL generation.
Max 3 attempts: syntax fix → schema fix → logic fix.
"""

import logging
from typing import Dict, Any, Optional, Tuple, Callable

from sql_generation.sql_prompt_builder import build_retry_prompt

logger = logging.getLogger(__name__)


class RetryHandler:
    """
    Retry handler cho SQL pipeline.
    3 retry levels:
      1. Syntax fix
      2. Schema correction
      3. Logic correction
    """

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.attempts: list = []

    def should_retry(self) -> bool:
        return len(self.attempts) < self.max_retries

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

    def get_retry_prompt(
        self,
        error_type: str,
        sql: str,
        error_message: str,
        schema: str = "",
        question: str = "",
    ) -> str:
        """
        Build retry prompt phù hợp với loại lỗi.
        """
        retry_num = self.retry_count

        if retry_num == 1 or error_type == "syntax":
            return build_retry_prompt("syntax", sql, error_message)
        elif retry_num == 2 or error_type == "schema":
            return build_retry_prompt("schema", sql, error_message, schema=schema)
        else:
            return build_retry_prompt("logic", sql, error_message, schema=schema, question=question)

    def get_summary(self) -> Dict[str, Any]:
        return {
            "total_attempts": len(self.attempts),
            "max_retries": self.max_retries,
            "attempts": self.attempts,
        }
