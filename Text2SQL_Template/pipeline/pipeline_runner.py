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


def run_pipeline(question: str, use_embedding: bool = False) -> Dict[str, Any]:
    """
    Orchestrator chính.
    Chạy toàn bộ pipeline từ câu hỏi → kết quả + giải thích.
    """
    start_time = time.time()
    _ensure_loaded()

    log_entry = {
        "question": question,
        "intent": None,
        "intent_name": None,
        "intent_description": None,
        "intent_sql_template": None,
        "entities": {},
        "sql_generated": None,
        "validator_status": None,
        "retry_count": 0,
        "execution_time": 0,
        "result_count": 0,
        "explain": "",
        "error": None,
    }

    try:
        # ─── Step 1: Schema Router ──────────────────────────
        logger.info(f"\n{'='*60}")
        logger.info(f"[Step 1] Schema Router")
        tables = select_tables(question, _profiles, use_embedding=use_embedding)
        schema_desc = get_schema_description(_profiles, tables)
        logger.info(f"[Step 1] Selected tables: {tables}")

        # ─── Step 2: Intent Detection ───────────────────────
        logger.info(f"[Step 2] Intent Detection")
        intent = detect_intent(question, _intent_index, use_embedding=use_embedding)

        if intent:
            log_entry["intent"] = intent.get("intent_id")
            log_entry["intent_name"] = intent.get("intent_name", "")
            log_entry["intent_description"] = intent.get("description", "")
            log_entry["intent_sql_template"] = intent.get("sql_template", "")
            logger.info(f"[Step 2] Detected intent: {intent.get('intent_id')}")
            logger.info(f"[Step 2] Intent name: {intent.get('intent_name', '')}")
        else:
            logger.warning("[Step 2] No intent detected, proceeding without template hint")

        # ─── Step 3: Entity Extraction ──────────────────────
        logger.info(f"[Step 3] Entity Extraction")
        raw_entities = extract_entities_local(question)
        entities = normalize_entities(raw_entities)
        log_entry["entities"] = entities
        logger.info(f"[Step 3] Entities: {entities}")

        # ─── Step 4: Template Retrieval ─────────────────────
        logger.info(f"[Step 4] Template Retrieval")
        template_sql = ""
        if intent:
            template_sql = get_template_for_intent(intent, _approved_templates) or ""
            if template_sql and entities:
                filled_template, unfilled = fill_template(template_sql, entities)
                logger.info(f"[Step 4] Filled template (unfilled: {list(unfilled.keys())})")
            else:
                filled_template = template_sql

        # ─── Step 5: SQL Generation ─────────────────────────
        logger.info(f"[Step 5] SQL Generation")
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
        log_entry["sql_generated"] = sql

        # ─── Step 6: Validation + Retry ─────────────────────
        logger.info(f"[Step 6] Validation")
        retry = RetryHandler(max_retries=MAX_RETRY_ATTEMPTS)

        is_valid, error_msg, error_type = validate_all(sql, _profiles)
        log_entry["validator_status"] = "PASS" if is_valid else "FAIL"

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
            log_entry["sql_generated"] = sql

            is_valid, error_msg, error_type = validate_all(sql, _profiles)
            log_entry["validator_status"] = "PASS" if is_valid else "FAIL"

        log_entry["retry_count"] = retry.retry_count

        if not is_valid:
            log_entry["error"] = f"Validation failed after {retry.retry_count} retries: {error_msg}"
            log_entry["execution_time"] = time.time() - start_time
            _log_query(log_entry)
            return log_entry

        # ─── Step 7: Execute on DB ──────────────────────────
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
                log_entry["sql_generated"] = sql
                log_entry["retry_count"] = retry.retry_count

                is_valid, _, _ = validate_all(sql, _profiles)
                if is_valid:
                    success, rows, db_error = execute_query(sql)

            if not success:
                log_entry["error"] = f"DB execution failed: {db_error}"
                log_entry["execution_time"] = time.time() - start_time
                _log_query(log_entry)
                return log_entry

        log_entry["result_count"] = len(rows) if rows else 0

        # Save successful SQL as approved template
        if intent and rows:
            intent_id = intent.get("intent_id", "")
            if intent_id:
                save_approved_template(intent_id, sql)

        # ─── Step 8: Result Formatting + Explain ────────────
        logger.info(f"[Step 8] Explain & Format")
        explain_text = generate_explain(
            question=question,
            sql=sql,
            entities=entities,
            result_rows=rows,
            intent_name=intent.get("intent_name", "") if intent else "",
        )
        log_entry["explain"] = explain_text

        if rows:
            log_entry["result_table"] = format_result_table(rows)
            log_entry["result_data"] = rows

        log_entry["execution_time"] = time.time() - start_time
        _log_query(log_entry)

        logger.info(f"[Pipeline] Completed in {log_entry['execution_time']:.2f}s")
        return log_entry

    except Exception as e:
        log_entry["error"] = str(e)
        log_entry["execution_time"] = time.time() - start_time
        logger.error(f"[Pipeline] Error: {e}", exc_info=True)
        _log_query(log_entry)
        return log_entry


def _log_query(entry: Dict[str, Any]):
    """Log query entry sang file JSON."""
    import os
    from datetime import datetime
    from config.settings import LOGS_DIR

    os.makedirs(LOGS_DIR, exist_ok=True)
    log_file = os.path.join(LOGS_DIR, f"{datetime.now().strftime('%Y-%m-%d')}.jsonl")

    # Tạo bản log không chứa result_data (quá lớn)
    log_safe = {k: v for k, v in entry.items() if k not in ("result_data", "result_table")}

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_safe, ensure_ascii=False, default=str) + "\n")
