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
from validator.security_guard import validate_all, classify_execution_error
from validator.semantic_validator import validate_semantic
from validator.structure_validator import validate_sql_structure
from validator.data_validator import validate_empty_result
from validator.confidence_scorer import compute_confidence

# Executor
from executor.query_executor import execute_query, explain_query

# Explain
from explain.explain_engine import generate_explain, format_result_table

# Retry & Cache & Mock
from pipeline.retry_handler import RetryHandler
from pipeline.query_cache import get_cached_result, cache_result
from pipeline.test_mock import inject_test_account

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

    # ─── Cache check ────────────────────────────────────
    cached = get_cached_result(question)
    if cached:
        cached["execution_time"] = round(time.time() - start_time, 3)
        cached["timing"] = {"cache_hit": 0.0}
        logger.info(f"[Pipeline] Cache HIT → returning cached SQL")
        return cached

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
        "confidence": {},
        "semantic_warnings": [],
        "data_validation": None,
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

        # Inject test mock account nếu TEST_MODE
        sql = inject_test_account(sql)

        log_entry["sql"] = sql
        timing["sql_generation"] = round(time.time() - t0, 3)
        logger.info(f"[Step 5] ({timing['sql_generation']}s)")

        # ─── Step 6: Validation + Semantic Check + Retry ────────
        t0 = time.time()
        logger.info(f"[Step 6] Validation")
        retry = RetryHandler(max_retries=MAX_RETRY_ATTEMPTS)

        # 6a. Pre-execution validation (security + syntax + schema)
        is_valid, error_msg, error_type = validate_all(sql, _profiles)
        log_entry["validator"] = "PASS" if is_valid else "FAIL"

        while not is_valid and retry.should_retry(error_type):
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

        if not is_valid:
            log_entry["error"] = f"Validation failed after {retry.retry_count} retries: {error_msg}"
            log_entry["retry_count"] = retry.retry_count
            log_entry["execution_time"] = time.time() - start_time
            log_entry["timing"] = timing
            # Confidence: SQL không chạy được
            log_entry["confidence"] = compute_confidence(
                sql_executed=False, entity_valid=True, schema_valid=False,
                row_count=0, semantic_ok=False, structure_score=0.0,
            )
            _log_query(log_entry)
            return log_entry

        # 6b. Semantic validation (keyword check question vs SQL)
        semantic_ok, semantic_warnings = validate_semantic(question, sql)
        log_entry["semantic_warnings"] = semantic_warnings

        if not semantic_ok and retry.should_retry("semantic"):
            logger.warning(f"[Step 6] Semantic issues: {semantic_warnings}")
            retry.record_attempt(sql, "; ".join(semantic_warnings), "semantic")
            retry_prompt = retry.get_retry_prompt(
                error_type="semantic",
                sql=sql,
                error_message="; ".join(semantic_warnings),
                schema=schema_desc,
                question=question,
                semantic_warnings=semantic_warnings,
            )
            sql = generate_sql(retry_prompt)
            log_entry["sql"] = sql
            # Re-validate after semantic retry
            is_valid, error_msg, error_type = validate_all(sql, _profiles)
            if not is_valid:
                log_entry["validator"] = "FAIL"
                log_entry["error"] = f"Post-semantic-retry validation failed: {error_msg}"
                log_entry["retry_count"] = retry.retry_count
                log_entry["execution_time"] = time.time() - start_time
                log_entry["timing"] = timing
                _log_query(log_entry)
                return log_entry
            # Re-check semantic
            semantic_ok, semantic_warnings = validate_semantic(question, sql)
            log_entry["semantic_warnings"] = semantic_warnings

        # 6c. EXPLAIN pre-check (check syntax on DB without running full query)
        explain_ok, explain_err = explain_query(sql)
        if not explain_ok and retry.should_retry("syntax"):
            logger.warning(f"[Step 6] EXPLAIN failed: {explain_err}")
            retry.record_attempt(sql, explain_err, "syntax")
            retry_prompt = retry.get_retry_prompt(
                error_type="syntax",
                sql=sql,
                error_message=f"EXPLAIN failed: {explain_err}",
                schema=schema_desc,
                question=question,
            )
            sql = generate_sql(retry_prompt)
            log_entry["sql"] = sql
            explain_ok, explain_err = explain_query(sql)

        if not explain_ok:
            log_entry["error"] = f"EXPLAIN failed: {explain_err}"
            log_entry["validator"] = "FAIL"
            log_entry["retry_count"] = retry.retry_count
            log_entry["execution_time"] = time.time() - start_time
            log_entry["timing"] = timing
            log_entry["confidence"] = compute_confidence(
                sql_executed=False, entity_valid=True, schema_valid=True,
                row_count=0, semantic_ok=semantic_ok, structure_score=0.0,
            )
            _log_query(log_entry)
            return log_entry

        log_entry["retry_count"] = retry.retry_count
        timing["validation"] = round(time.time() - t0, 3)
        logger.info(f"[Step 6] ({timing['validation']}s)")

        # ─── Step 7: Execute on DB + Smart Result Handling ──
        t0 = time.time()
        logger.info(f"[Step 7] Execute on DB")
        success, rows, db_error = execute_query(sql)

        if not success:
            # Phân loại lỗi DB
            exec_error_type = classify_execution_error(db_error)
            logger.warning(f"[Step 7] DB error ({exec_error_type}): {db_error}")

            if exec_error_type in ("syntax", "runtime") and retry.should_retry(exec_error_type):
                retry.record_attempt(sql, db_error, exec_error_type)
                retry_prompt = retry.get_retry_prompt(
                    error_type=exec_error_type,
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
                log_entry["error"] = f"DB execution failed ({exec_error_type}): {db_error}"
                log_entry["execution_time"] = time.time() - start_time
                log_entry["timing"] = timing
                log_entry["confidence"] = compute_confidence(
                    sql_executed=False, entity_valid=True, schema_valid=True,
                    row_count=0, semantic_ok=semantic_ok, structure_score=0.0,
                )
                _log_query(log_entry)
                return log_entry

        row_count = len(rows) if rows else 0
        log_entry["rows"] = row_count

        # ─── Step 7b: SQL Structure Validation (primary check) ──
        # Dùng structure validator thay vì row count làm tiêu chí chính
        struct_valid, struct_issues, struct_score = validate_sql_structure(
            sql=sql,
            question=question,
            entities=entities,
            profiles=_profiles,
            intent=intent,
        )
        log_entry["structure_score"] = struct_score
        log_entry["structure_issues"] = struct_issues

        # ─── Step 7c: Handle row = 0 (data validation, NOT fail) ──
        entity_valid = True
        if row_count == 0 and success:
            if struct_valid:
                # SQL structure đúng → row=0 là do data không có (PASS_EMPTY)
                log_entry["validator"] = "PASS_EMPTY"
                logger.info(f"[Step 7] PASS_EMPTY: SQL structure OK (score={struct_score}), data rỗng")
            else:
                # SQL structure có vấn đề + row=0 → chạy data validation thêm
                logger.info("[Step 7] row=0 + structure issues → running data validation...")
                data_result = validate_empty_result(
                    sql=sql,
                    entities=entities,
                    profiles=_profiles,
                    executor_fn=execute_query,
                )
                log_entry["data_validation"] = data_result

                if data_result["status"] == "DATA_ERROR":
                    log_entry["validator"] = "DATA_ERROR"
                    log_entry["error"] = data_result["message"]
                    entity_valid = False
                    logger.warning(f"[Step 7] DATA_ERROR: {data_result['message']}")
                else:
                    log_entry["validator"] = "PASS_EMPTY"
                    logger.info(f"[Step 7] PASS_EMPTY: {data_result['message']}")

        # ─── Confidence scoring (structure-first, not row-count) ──
        log_entry["confidence"] = compute_confidence(
            sql_executed=success,
            entity_valid=entity_valid,
            schema_valid=True,  # passed Step 6a
            row_count=row_count,
            semantic_ok=semantic_ok,
            structure_score=struct_score,
        )

        timing["execution"] = round(time.time() - t0, 3)
        logger.info(f"[Step 7] ({timing['execution']}s)")

        # Save successful SQL as approved template (only when rows > 0)
        if intent and rows and row_count > 0:
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

        # Cache successful results
        cache_result(question, log_entry)

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
        "confidence": entry.get("confidence", {}),
        "timing": entry.get("timing", {}),
    }
    if entry.get("error"):
        log_record["error"] = entry["error"]
    if entry.get("semantic_warnings"):
        log_record["semantic_warnings"] = entry["semantic_warnings"]
    if entry.get("data_validation"):
        log_record["data_validation"] = entry["data_validation"]
    if entry.get("structure_score") is not None:
        log_record["structure_score"] = entry["structure_score"]
    if entry.get("structure_issues"):
        log_record["structure_issues"] = entry["structure_issues"]

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_record, ensure_ascii=False, default=str) + "\n")
