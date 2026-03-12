"""
Pipeline – Retry Handler
Quản lý retry strategy cho SQL generation.

Logic:
  syntax_error  → retry SQL (max 2)
  runtime_error → retry SQL hoặc fallback template
  row=0         → data validation (không retry bừa)
  connection    → không retry
"""

import logging
from typing import Dict, Any, Optional, Tuple, Callable

from sql_generation.sql_prompt_builder import build_retry_prompt

logger = logging.getLogger(__name__)


class RetryHandler:
    """
    Smart retry handler:
    - Phân loại lỗi trước khi retry
    - Max 2 retries cho syntax/runtime
    - Không retry connection errors
    - Row=0 → delegate cho data validator
    """

    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries
        self.attempts: list = []

    def should_retry(self, error_type: str = "") -> bool:
        """Chỉ retry nếu lỗi có thể sửa được."""
        if error_type in ("connection", "security"):
            return False
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
