"""
Executor – Query Executor
Execute SQL trên database với safety limits (LIMIT, timeout).
Hỗ trợ hai engine:
  - mysql  : mysql.connector (banking và các domain dùng MySQL)
  - sqlite : sqlite3 built-in (hrm mock và các domain dùng file SQLite)
"""

import logging
import sqlite3
import time
from typing import Dict, List, Any, Tuple, Optional

try:
    import mysql.connector
    from mysql.connector import pooling as mysql_pooling
except ImportError:
    mysql = None
    mysql_pooling = None

from config.settings import (
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME,
    QUERY_ROW_LIMIT, QUERY_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)

# Pool per DB: key = "host:port/database"
_mysql_pools: Dict[str, Any] = {}
_POOL_SIZE = 5


def _get_mysql_pool(config: Dict[str, Any]) -> Any:
    """Lấy hoặc tạo connection pool cho một db_config."""
    key = f"{config['host']}:{config['port']}/{config['database']}"
    if key not in _mysql_pools:
        _mysql_pools[key] = mysql_pooling.MySQLConnectionPool(
            pool_name=f"pool_{len(_mysql_pools)}",
            pool_size=_POOL_SIZE,
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            database=config["database"],
        )
        logger.info(f"[Executor][MySQL] Created pool for {key} (size={_POOL_SIZE})")
    return _mysql_pools[key]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_db_config(db_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    config = {
        "engine": "mysql",
        "host": DB_HOST,
        "port": DB_PORT,
        "user": DB_USER,
        "password": DB_PASSWORD,
        "database": DB_NAME,
    }
    if db_config:
        config.update({k: v for k, v in db_config.items() if v is not None})
    return config


def _ensure_limit(sql: str, row_limit: int) -> str:
    """Thêm LIMIT nếu SQL chưa có."""
    if "LIMIT" not in sql.upper():
        sql = sql.rstrip(";").strip()
        sql = f"{sql}\nLIMIT {row_limit};"
    return sql


# ── SQLite backend ────────────────────────────────────────────────────────────

def _execute_sqlite(
    sql: str,
    params: Optional[List[str]],
    db_path: str,
    row_limit: int,
) -> Tuple[bool, Any, str]:
    start_time = time.time()
    conn = None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row          # trả về dict-like rows
        cur = conn.cursor()

        if params:
            cur.execute(sql, params)
        else:
            cur.execute(sql)

        raw_rows = cur.fetchall()
        rows = [dict(r) for r in raw_rows]      # chuyển sang list[dict] như MySQL
        elapsed = time.time() - start_time

        cur.close()
        logger.info(f"[Executor][SQLite] {len(rows)} rows in {elapsed:.2f}s")
        return True, rows, ""

    except sqlite3.Error as e:
        elapsed = time.time() - start_time
        error_msg = str(e)
        logger.error(f"[Executor][SQLite] Error after {elapsed:.2f}s: {error_msg}")
        return False, None, error_msg
    finally:
        if conn:
            conn.close()


# ── MySQL backend ─────────────────────────────────────────────────────────────

def _execute_mysql(
    sql: str,
    params: Optional[List[str]],
    conn_config: Dict[str, Any],
    timeout: int,
) -> Tuple[bool, Any, str]:
    if mysql is None:
        logger.warning("[Executor][MySQL] mysql-connector-python not installed")
        return False, None, "mysql-connector-python not installed"

    start_time = time.time()
    conn = None
    try:
        pool = _get_mysql_pool(conn_config)
        conn = pool.get_connection()
        cursor = conn.cursor(dictionary=True)

        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        rows = cursor.fetchall()
        elapsed = time.time() - start_time

        cursor.close()
        logger.info(f"[Executor][MySQL] {len(rows)} rows in {elapsed:.2f}s")
        return True, rows, ""

    except Exception as e:
        elapsed = time.time() - start_time
        error_msg = str(e)
        logger.error(f"[Executor][MySQL] Error after {elapsed:.2f}s: {error_msg}")
        return False, None, error_msg

    finally:
        if conn and conn.is_connected():
            conn.close()  # trả connection về pool


# ── Public API ────────────────────────────────────────────────────────────────

def execute_query(
    sql: str,
    params: Optional[List[str]] = None,
    row_limit: int = QUERY_ROW_LIMIT,
    timeout: int = QUERY_TIMEOUT_SECONDS,
    db_config: Optional[Dict[str, Any]] = None,
) -> Tuple[bool, Any, str]:
    """
    Execute SQL trên database.
    Route tự động theo db_config["engine"]: "sqlite" | "mysql" (default).
    Returns: (success, result_rows_or_None, error_message)
    """
    sql = _ensure_limit(sql, row_limit)
    config = _resolve_db_config(db_config)
    logger.info(f"[Executor] SQL: {sql[:300]}...")

    if config.get("engine") == "sqlite":
        return _execute_sqlite(sql, params, config["database"], row_limit)

    return _execute_mysql(sql, params, config, timeout)


def explain_query(sql: str, db_config: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
    """
    Validate SQL syntax trước khi execute thật.
    - SQLite: dùng EXPLAIN QUERY PLAN (không raise nếu syntax ok)
    - MySQL : dùng EXPLAIN
    Returns: (is_valid, error_message)
    """
    config = _resolve_db_config(db_config)

    if config.get("engine") == "sqlite":
        try:
            conn = sqlite3.connect(config["database"])
            cur = conn.cursor()
            cur.execute(f"EXPLAIN QUERY PLAN {sql.rstrip(';')}")
            cur.fetchall()
            conn.close()
            return True, ""
        except sqlite3.Error as e:
            logger.warning(f"[Executor][SQLite] EXPLAIN failed: {e}")
            return False, str(e)

    # MySQL path
    if mysql is None:
        return True, ""

    conn = None
    try:
        pool = _get_mysql_pool(config)
        conn = pool.get_connection()
        cursor = conn.cursor()
        cursor.execute(f"EXPLAIN {sql.rstrip(';')}")
        cursor.fetchall()
        cursor.close()
        return True, ""
    except Exception as e:
        error_msg = str(e)
        logger.warning(f"[Executor][MySQL] EXPLAIN failed: {error_msg}")
        return False, error_msg
    finally:
        if conn and conn.is_connected():
            conn.close()  # trả connection về pool
