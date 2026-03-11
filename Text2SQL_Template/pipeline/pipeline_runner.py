"""
Pipeline – Pipeline Runner
Orchestrator chính: điều phối toàn bộ luồng Text2SQL.
"""

import json
import time
import logging
from typing import Dict, Any, Optional

from config.settings import MAX_RETRY_ATTEMPTS, QUERY_ROW_LIMIT

# Schema router
from schema_router.schema_loader import load_all_profiles, get_schema_description
from schema_router.table_selector import select_tables

# Intent detection
from intent_detection.intent_loader import load_intent_dataset, build_intent_index
from intent_detection.intent_ranker import detect_intent

# Entity extraction
from entity_extraction.ner_local import extract_entities_local

# Slot filling
from slot_filling.entity_normalizer import normalize_entities
from slot_filling.slot_filler import fill_template

# Template store
from template_store.template_loader import (
    load_approved_templates,
    get_template_for_intent,
    save_approved_template,
)

# SQL generation
from sql_generation.sql_prompt_builder import build_sql_prompt
from sql_generation.llm_sql_generator import generate_sql

# Validator
from validator.security_guard import validate_all

# Executor
from executor.query_executor import execute_query

# Explain
from explain.explain_engine import generate_explain, format_result_table

# Retry
from pipeline.retry_handler import RetryHandler

logger = logging.getLogger(__name__)


# ─── Cached resources (loaded once) ─────────────────────────
_profiles = None
_intent_index = None
_approved_templates = None


def _ensure_loaded():
    """Lazy load tất cả resources cần thiết."""
    global _profiles, _intent_index, _approved_templates

    if _profiles is None:
        logger.info("[Pipeline] Loading semantic profiles...")
        _profiles = load_all_profiles()

    if _intent_index is None:
        logger.info("[Pipeline] Loading intent dataset...")
        dataset = load_intent_dataset()
        _intent_index = build_intent_index(dataset)

    if _approved_templates is None:
        logger.info("[Pipeline] Loading approved templates...")
        _approved_templates = load_approved_templates()


def run_pipeline(question: str, use_embedding: bool = False, explain: bool = True) -> Dict[str, Any]:
    """
    Orchestrator chính.
    Chạy toàn bộ pipeline từ câu hỏi → kết quả + giải thích.
    """
    start_time = time.time()
    _ensure_loaded()

    timing: Dict[str, float] = {}

    log_entry = {
        "question": question,
        "tables": [],
        "intent": None,
        "intent_name": None,
        "intent_description": None,
        "intent_sql_template": None,
        "entities": {},
        "sql": None,
        "validator": None,
        "retry_count": 0,
        "rows": 0,
        "execution_time": 0,
        "timing": {},
        "explain": "",
        "error": None,
    }

    try:
        # ─── Step 1: Schema Router ──────────────────────────
        t0 = time.time()
        logger.info(f"\n{'='*60}")
        logger.info(f"[Step 1] Schema Router")
        tables = select_tables(question, _profiles, use_embedding=use_embedding)
        schema_desc = get_schema_description(_profiles, tables)
        log_entry["tables"] = tables
        timing["schema_router"] = round(time.time() - t0, 3)
        logger.info(f"[Step 1] Selected tables: {tables} ({timing['schema_router']}s)")

        # ─── Step 2: Intent Detection ───────────────────────
        t0 = time.time()
        logger.info(f"[Step 2] Intent Detection")
        intent = detect_intent(question, _intent_index, use_embedding=use_embedding)

        if intent:
            log_entry["intent"] = intent.get("intent_id")
            log_entry["intent_name"] = intent.get("intent_name", "")
            log_entry["intent_description"] = intent.get("description", "")
            log_entry["intent_sql_template"] = intent.get("sql_template", "")
            logger.info(f"[Step 2] Detected intent: {intent.get('intent_id')}")
        else:
            logger.warning("[Step 2] No intent detected, proceeding without template hint")
        timing["intent_detection"] = round(time.time() - t0, 3)
        logger.info(f"[Step 2] ({timing['intent_detection']}s)")

        # ─── Step 3: Entity Extraction ──────────────────────
        t0 = time.time()
        logger.info(f"[Step 3] Entity Extraction")
        raw_entities = extract_entities_local(question)
        entities = normalize_entities(raw_entities)
        log_entry["entities"] = entities
        timing["entity_extraction"] = round(time.time() - t0, 3)
        logger.info(f"[Step 3] Entities: {entities} ({timing['entity_extraction']}s)")

        # ─── Step 4: Template Retrieval + Slot Filling ──────
        t0 = time.time()
        logger.info(f"[Step 4] Template Retrieval")
        template_sql = ""
        filled_template = ""
        unfilled = {}
        template_complete = False

        if intent:
            template_sql = get_template_for_intent(intent, _approved_templates) or ""
            if template_sql and entities:
                filled_template, unfilled = fill_template(template_sql, entities)
                template_complete = len(unfilled) == 0
                logger.info(f"[Step 4] Template complete: {template_complete} (unfilled: {list(unfilled.keys())})")
            else:
                filled_template = template_sql

        timing["template_fill"] = round(time.time() - t0, 3)
        logger.info(f"[Step 4] ({timing['template_fill']}s)")

        # ─── Step 5: SQL Generation ─────────────────────────
        # Template-first: skip LLM if template fills completely
        t0 = time.time()
        if template_complete and filled_template:
            logger.info(f"[Step 5] Template-fill complete → skip LLM")
            sql = filled_template
        else:
            logger.info(f"[Step 5] SQL Generation (LLM)")
            prompt = build_sql_prompt(
                question=question,
                schema_description=schema_desc,
                intent_name=intent.get("intent_id", "") if intent else "",
                intent_description=intent.get("description", "") if intent else "",
                entities=entities,
                template_sql=template_sql,
                row_limit=QUERY_ROW_LIMIT,
            )
            sql = generate_sql(prompt)

        log_entry["sql"] = sql
        timing["sql_generation"] = round(time.time() - t0, 3)
        logger.info(f"[Step 5] ({timing['sql_generation']}s)")

        # ─── Step 6: Validation + Retry ─────────────────────
        t0 = time.time()
        logger.info(f"[Step 6] Validation")
        retry = RetryHandler(max_retries=MAX_RETRY_ATTEMPTS)

        is_valid, error_msg, error_type = validate_all(sql, _profiles)
        log_entry["validator"] = "PASS" if is_valid else "FAIL"

        while not is_valid and retry.should_retry():
            retry.record_attempt(sql, error_msg, error_type)
            logger.warning(f"[Step 6] Validation failed ({error_type}): {error_msg}")
            logger.info(f"[Step 6] Retry #{retry.retry_count}")

            retry_prompt = retry.get_retry_prompt(
                error_type=error_type,
                sql=sql,
                error_message=error_msg,
                schema=schema_desc,
                question=question,
            )
            sql = generate_sql(retry_prompt)
            log_entry["sql"] = sql

            is_valid, error_msg, error_type = validate_all(sql, _profiles)
            log_entry["validator"] = "PASS" if is_valid else "FAIL"

        log_entry["retry_count"] = retry.retry_count
        timing["validation"] = round(time.time() - t0, 3)
        logger.info(f"[Step 6] ({timing['validation']}s)")

        if not is_valid:
            log_entry["error"] = f"Validation failed after {retry.retry_count} retries: {error_msg}"
            log_entry["execution_time"] = time.time() - start_time
            log_entry["timing"] = timing
            _log_query(log_entry)
            return log_entry

        # ─── Step 7: Execute on DB ──────────────────────────
        t0 = time.time()
        logger.info(f"[Step 7] Execute on DB")
        success, rows, db_error = execute_query(sql)

        if not success:
            # DB error → retry
            if retry.should_retry():
                retry.record_attempt(sql, db_error, "execution")
                retry_prompt = retry.get_retry_prompt(
                    error_type="syntax",
                    sql=sql,
                    error_message=db_error,
                    schema=schema_desc,
                    question=question,
                )
                sql = generate_sql(retry_prompt)
                log_entry["sql"] = sql
                log_entry["retry_count"] = retry.retry_count

                is_valid, _, _ = validate_all(sql, _profiles)
                if is_valid:
                    success, rows, db_error = execute_query(sql)

            if not success:
                log_entry["error"] = f"DB execution failed: {db_error}"
                log_entry["execution_time"] = time.time() - start_time
                log_entry["timing"] = timing
                _log_query(log_entry)
                return log_entry

        log_entry["rows"] = len(rows) if rows else 0
        timing["execution"] = round(time.time() - t0, 3)
        logger.info(f"[Step 7] ({timing['execution']}s)")

        # Save successful SQL as approved template
        if intent and rows:
            intent_id = intent.get("intent_id", "")
            if intent_id:
                save_approved_template(intent_id, sql)

        # ─── Step 8: Result Formatting + Explain ────────────
        if explain:
            t0 = time.time()
            logger.info(f"[Step 8] Explain & Format")
            explain_text = generate_explain(
                question=question,
                sql=sql,
                entities=entities,
                result_rows=rows,
                intent_name=intent.get("intent_name", "") if intent else "",
            )
            log_entry["explain"] = explain_text
            timing["explain"] = round(time.time() - t0, 3)
            logger.info(f"[Step 8] ({timing['explain']}s)")
        else:
            logger.info(f"[Step 8] Explain skipped (--no-explain)")

        if rows:
            log_entry["result_table"] = format_result_table(rows)
            log_entry["result_data"] = rows

        log_entry["execution_time"] = round(time.time() - start_time, 3)
        log_entry["timing"] = timing
        _log_query(log_entry)

        logger.info(f"[Pipeline] Completed in {log_entry['execution_time']}s")
        _print_timing(timing)
        return log_entry

    except Exception as e:
        log_entry["error"] = str(e)
        log_entry["execution_time"] = round(time.time() - start_time, 3)
        log_entry["timing"] = timing
        logger.error(f"[Pipeline] Error: {e}", exc_info=True)
        _log_query(log_entry)
        return log_entry


def _print_timing(timing: Dict[str, float]):
    """Print timing breakdown cho mỗi step."""
    logger.info("[Timing] ─── Step Breakdown ───")
    for step, elapsed in timing.items():
        logger.info(f"  {step:20s} {elapsed:6.3f}s")
    total = sum(timing.values())
    logger.info(f"  {'TOTAL':20s} {total:6.3f}s")


# ─── Per-run log file (set once per app.py invocation) ──────
_queries_log_file = None


def _get_queries_log_file() -> str:
    """Trả về path log file cho lần chạy hiện tại (tạo 1 lần duy nhất)."""
    global _queries_log_file
    if _queries_log_file is None:
        import os
        from datetime import datetime
        from config.settings import LOGS_DIR

        queries_dir = os.path.join(LOGS_DIR, "queries")
        os.makedirs(queries_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        _queries_log_file = os.path.join(queries_dir, f"{ts}.jsonl")
    return _queries_log_file


def _log_query(entry: Dict[str, Any]):
    """Log query entry sang file JSONL theo format chuẩn."""
    log_file = _get_queries_log_file()

    log_record = {
        "question": entry.get("question"),
        "tables": entry.get("tables", []),
        "intent": entry.get("intent"),
        "entities": entry.get("entities", {}),
        "sql": entry.get("sql"),
        "validator": entry.get("validator"),
        "rows": entry.get("rows", 0),
        "timing": entry.get("timing", {}),
    }
    if entry.get("error"):
        log_record["error"] = entry["error"]

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_record, ensure_ascii=False, default=str) + "\n")
