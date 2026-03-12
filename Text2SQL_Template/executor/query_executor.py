"""
Executor – Query Executor
Execute SQL trên database với safety limits (LIMIT, timeout).
"""

import logging
import time
from typing import Dict, List, Any, Tuple, Optional

try:
    import mysql.connector
except ImportError:
    mysql = None

from config.settings import (
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME,
    QUERY_ROW_LIMIT, QUERY_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


def execute_query(
    sql: str,
    params: Optional[List[str]] = None,
    row_limit: int = QUERY_ROW_LIMIT,
    timeout: int = QUERY_TIMEOUT_SECONDS,
) -> Tuple[bool, Any, str]:
    """
    Execute SQL trên database.
    Returns: (success, result_rows_or_None, error_message)
    """
    # Inject LIMIT nếu chưa có
    sql = _ensure_limit(sql, row_limit)

    if mysql is None:
        logger.warning("[Executor] mysql-connector-python not installed, skipping DB execution")
        return False, None, "mysql-connector-python not installed"

    logger.info(f"[Executor] Executing SQL: {sql[:300]}...")
    start_time = time.time()

    conn = None
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            connection_timeout=timeout,
        )
        cursor = conn.cursor(dictionary=True)

        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        rows = cursor.fetchall()
        elapsed = time.time() - start_time

        logger.info(f"[Executor] Returned {len(rows)} rows in {elapsed:.2f}s")

        cursor.close()
        return True, rows, ""

    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = str(e)
        logger.error(f"[Executor] DB error after {elapsed:.2f}s: {error_msg}")
        return False, None, error_msg

    finally:
        if conn and conn.is_connected():
            conn.close()


def _ensure_limit(sql: str, row_limit: int) -> str:
    """Thêm LIMIT nếu SQL chưa có."""
    if "LIMIT" not in sql.upper():
        sql = sql.rstrip(";").strip()
        sql = f"{sql}\nLIMIT {row_limit};"
    return sql


def explain_query(sql: str) -> Tuple[bool, str]:
    """
    Chạy EXPLAIN trước khi execute thật.
    Nếu EXPLAIN fail → SQL có syntax error, tránh chạy full query.
    Returns: (is_valid, error_message)
    """
    if mysql is None:
        return True, ""  # Không có DB → skip check

    conn = None
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            connection_timeout=5,
        )
        cursor = conn.cursor()
        explain_sql = f"EXPLAIN {sql.rstrip(';')}"
        cursor.execute(explain_sql)
        cursor.fetchall()
        cursor.close()
        return True, ""
    except Exception as e:
        error_msg = str(e)
        logger.warning(f"[Executor] EXPLAIN failed: {error_msg}")
        return False, error_msg
    finally:
        if conn and conn.is_connected():
            conn.close()
