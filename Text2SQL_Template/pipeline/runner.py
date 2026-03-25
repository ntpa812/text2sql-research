"""
Pipeline – Pipeline Runner
Orchestrator chính: điều phối toàn bộ luồng Text2SQL.
"""

import json
import logging
import time
from typing import Any, Dict, Optional

from config.settings import MAX_RETRY_ATTEMPTS, QUERY_ROW_LIMIT

from pipeline.domain_router.registry_loader import get_domain_config, load_domain_registry
from pipeline.domain_router.selector import route_domains

from pipeline.schema_router.schema_loader import get_schema_description, load_all_profiles
from pipeline.schema_router.table_selector import rank_tables

from pipeline.intent_detection.intent_loader import build_intent_index, load_intent_dataset
from pipeline.intent_detection.intent_ranker import rank_intents

from pipeline.entity_extraction.ner_local import extract_entities_local

from pipeline.slot_filling.entity_normalizer import normalize_entities
from pipeline.slot_filling.slot_filler import fill_template

from pipeline.template_store.template_loader import (
    get_template_for_intent,
    load_approved_templates,
    save_approved_template,
)

from pipeline.sql_generation.sql_prompt_builder import build_sql_prompt
from pipeline.sql_generation.llm_sql_generator import generate_sql, get_generation_config, get_last_generation_info

from pipeline.validator.security_guard import classify_execution_error, validate_all
from pipeline.validator.semantic_validator import validate_semantic
from pipeline.validator.structure_validator import validate_sql_structure
from pipeline.validator.data_validator import validate_empty_result
from pipeline.validator.confidence_scorer import compute_confidence

from pipeline.executor.query_executor import execute_query, explain_query

from pipeline.explain.explain_engine import format_result_table, generate_explain

from pipeline.retry_handler import RetryHandler
from pipeline.query_cache import cache_result, get_cached_result
from pipeline.test_mock import inject_test_account
from pipeline.demo_cache import get_demo_rows

logger = logging.getLogger(__name__)

# ── Domain arbitration weights (tổng = 1.0) ──────────────────────────────────
ARBITRATION_WEIGHT_DOMAIN = 0.5   # trọng số domain routing score
ARBITRATION_WEIGHT_TABLE  = 0.2   # trọng số table relevance score
ARBITRATION_WEIGHT_INTENT = 0.3   # trọng số intent match score

# ── Table selection threshold ─────────────────────────────────────────────────
TABLE_SELECTION_MIN_SCORE = 0.3   # normalized score tối thiểu để table được chọn

# ── Intent ranking top-k ──────────────────────────────────────────────────────
INTENT_RANKING_TOP_K = 3


_registry = None
_domain_resources: Dict[str, Dict[str, Any]] = {}
_queries_log_file = None


def _ensure_registry_loaded() -> Dict[str, Any]:
    global _registry
    if _registry is None:
        logger.info("[Pipeline] Loading domain registry...")
        _registry = load_domain_registry()
    return _registry


def _ensure_domain_resources(domain_id: str) -> Dict[str, Any]:
    global _domain_resources

    if domain_id in _domain_resources:
        return _domain_resources[domain_id]

    registry = _ensure_registry_loaded()
    config = get_domain_config(registry, domain_id)
    paths = config.get("paths", {})

    logger.info(f"[Pipeline] Loading resources for domain={domain_id}...")
    profiles = load_all_profiles(path=paths.get("semantic_profiles_dir"), domain_id=domain_id)
    dataset = load_intent_dataset(path=paths.get("intent_dataset_path"), domain_id=domain_id)
    intent_index = build_intent_index(dataset, domain_id=domain_id)
    approved_templates = load_approved_templates(path=paths.get("approved_templates_dir"), domain_id=domain_id)

    _domain_resources[domain_id] = {
        "config": config,
        "paths": paths,
        "profiles": profiles,
        "intent_index": intent_index,
        "approved_templates": approved_templates,
        "db_config": config.get("db_config", {}),
    }
    return _domain_resources[domain_id]


def _strip_scores(item: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not item:
        return item
    return {k: v for k, v in item.items() if not k.startswith("_")}


def _select_tables_from_ranked(ranked_tables: list[Dict[str, Any]]) -> list[str]:
    if not ranked_tables:
        return []
    selected = [item["table_name"] for item in ranked_tables if item.get("_normalized_score", 0.0) >= TABLE_SELECTION_MIN_SCORE]
    if selected:
        return selected
    return [ranked_tables[0]["table_name"]]


def _build_demo_sql_fallback(table_names: list[str]) -> str:
    table_name = table_names[0] if table_names else "transaction"
    return f"SELECT * FROM {table_name} LIMIT 20;"


def _generate_sql_with_demo_fallback(
    prompt: str,
    demo_mode: bool,
    table_names: list[str],
    template_sql: str = "",
) -> tuple[str, Dict[str, Any]]:
    safe_template_sql = template_sql if isinstance(template_sql, str) else ""
    if safe_template_sql.strip().lower() in {"nan", "none", "null"}:
        safe_template_sql = ""
    try:
        sql = generate_sql(prompt)
        return sql, (get_last_generation_info() or get_generation_config())
    except Exception as exc:
        if not demo_mode:
            raise
        logger.warning(f"[LLM] Demo mode fallback SQL activated: {exc}")
        sql = safe_template_sql or _build_demo_sql_fallback(table_names)
        return sql, {
            **get_generation_config(),
            "active_model": "demo-sql-fallback",
            "active_backend": "demo",
            "used_fallback": True,
            "error": str(exc),
        }


def _serialize_ranked_domains(ranked_domains: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    serialized = []
    for item in ranked_domains:
        serialized.append({
            "domain_id": item.get("domain_id"),
            "display_name": item.get("display_name"),
            "score": round(item.get("_normalized_score", 0.0), 4),
            "keyword_score": round(item.get("_keyword_normalized_score", 0.0), 4),
            "matched_keywords": item.get("matched_keywords", []),
        })
    return serialized


def _arbitrate_domain(
    route_result: Dict[str, Any],
    table_rankings: Dict[str, Dict[str, Any]],
    intent_rankings: Dict[str, Dict[str, Any]],
    registry: Dict[str, Any],
) -> Dict[str, Any]:
    domain_scores = {
        item["domain_id"]: item.get("_normalized_score", 0.0)
        for item in route_result.get("ranked_domains", [])
    }
    arbitration = []

    for domain_id in route_result.get("candidate_domains", []):
        top_table = table_rankings.get(domain_id, {}).get("top_score", 0.0)
        top_intent = intent_rankings.get(domain_id, {}).get("top_score", 0.0)
        domain_score = domain_scores.get(domain_id, 0.0)
        final_score = (ARBITRATION_WEIGHT_DOMAIN * domain_score) + (ARBITRATION_WEIGHT_TABLE * top_table) + (ARBITRATION_WEIGHT_INTENT * top_intent)
        arbitration.append({
            "domain_id": domain_id,
            "display_name": registry["domains"][domain_id].get("display_name", domain_id),
            "domain_score": round(domain_score, 4),
            "table_score": round(top_table, 4),
            "intent_score": round(top_intent, 4),
            "final_score": round(final_score, 4),
        })

    arbitration.sort(key=lambda item: item["final_score"], reverse=True)
    selected_domain = arbitration[0]["domain_id"] if arbitration else None
    reason = "single_candidate" if len(arbitration) == 1 else "weighted_domain_table_intent"
    ambiguous = False

    if len(arbitration) > 1:
        diff = arbitration[0]["final_score"] - arbitration[1]["final_score"]
        if diff <= registry.get("ambiguity_tolerance", 0.05):
            ambiguous = True
            selected_domain = None
            reason = f"domain_ambiguous(diff={diff:.4f})"

    return {
        "selected_domain": selected_domain,
        "ambiguous": ambiguous,
        "reason": reason,
        "scores": arbitration,
    }


def run_pipeline(
    question: str,
    use_embedding: bool = False,
    explain: bool = True,
    forced_domain: str | None = None,
    demo_mode: bool = False,
    user_context: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Orchestrator chính.
    Chạy toàn bộ pipeline từ câu hỏi → kết quả + giải thích.
    """
    start_time = time.time()
    registry = _ensure_registry_loaded()

    timing: Dict[str, float] = {}
    log_entry = {
        "question": question,
        "domain": None,
        "candidate_domains": [],
        "domain_routing": {},
        "domain_tables": {},
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
        "model_info": get_generation_config(),
        "debug": {
            "question": question,
            "schema_description": "",
            "prompt": "",
            "template_sql": "",
            "execution_mode": "demo_cache" if demo_mode else "live",
        },
    }

    try:
        logger.info(f"\n{'=' * 60}")

        # ─── Step 0: Domain Router ──────────────────────────
        t0 = time.time()
        logger.info("[Step 0] Domain Router")
        route_result = route_domains(
            question=question,
            registry=registry,
            use_embedding=use_embedding,
            forced_domain=forced_domain,
        )
        timing["domain_router"] = round(time.time() - t0, 3)
        log_entry["candidate_domains"] = route_result.get("candidate_domains", [])
        log_entry["domain_routing"] = {
            "ranked_domains": _serialize_ranked_domains(route_result.get("ranked_domains", [])),
            "selected_domain": route_result.get("selected_domain"),
            "arbitration_reason": route_result.get("reason"),
        }
        logger.info(
            f"[Step 0] Candidate domains: {log_entry['candidate_domains']} "
            f"({timing['domain_router']}s)"
        )

        candidate_domains = route_result.get("candidate_domains", [])
        if not candidate_domains:
            log_entry["validator"] = "DOMAIN_AMBIGUOUS"
            log_entry["error"] = "No domain candidate matched the question."
            log_entry["execution_time"] = round(time.time() - start_time, 3)
            log_entry["timing"] = timing
            _log_query(log_entry)
            return log_entry

        # ─── Step 1: Schema Router per candidate domain ─────
        t0 = time.time()
        logger.info("[Step 1] Schema Router")
        table_rankings: Dict[str, Dict[str, Any]] = {}
        for domain_id in candidate_domains:
            resources = _ensure_domain_resources(domain_id)
            ranked_tables = rank_tables(
                question=question,
                profiles=resources["profiles"],
                use_embedding=use_embedding,
                table_keyword_map=resources["config"].get("table_keywords"),
            )
            selected_tables = _select_tables_from_ranked(ranked_tables)
            table_rankings[domain_id] = {
                "ranked_tables": ranked_tables,
                "selected_tables": selected_tables,
                "top_score": ranked_tables[0].get("_normalized_score", 0.0) if ranked_tables else 0.0,
            }
            log_entry["domain_tables"][domain_id] = selected_tables
        timing["schema_router"] = round(time.time() - t0, 3)
        logger.info(f"[Step 1] Domain tables: {log_entry['domain_tables']} ({timing['schema_router']}s)")

        # ─── Step 2: Intent Detection per candidate domain ───
        t0 = time.time()
        logger.info("[Step 2] Intent Detection")
        intent_rankings: Dict[str, Dict[str, Any]] = {}
        for domain_id in candidate_domains:
            resources = _ensure_domain_resources(domain_id)
            ranked_intents = rank_intents(
                question=question,
                intent_index=resources["intent_index"],
                use_embedding=use_embedding,
                top_k=INTENT_RANKING_TOP_K,
            )
            intent_rankings[domain_id] = {
                "ranked_intents": ranked_intents,
                "top_score": ranked_intents[0].get("_normalized_score", 0.0) if ranked_intents else 0.0,
            }
        timing["intent_detection"] = round(time.time() - t0, 3)

        arbitration = _arbitrate_domain(route_result, table_rankings, intent_rankings, registry)
        log_entry["domain_routing"]["selected_domain"] = arbitration["selected_domain"]
        log_entry["domain_routing"]["arbitration_reason"] = arbitration["reason"]
        log_entry["domain_routing"]["arbitration_scores"] = arbitration["scores"]

        if arbitration["ambiguous"] or not arbitration["selected_domain"]:
            log_entry["validator"] = "DOMAIN_AMBIGUOUS"
            log_entry["error"] = f"Domain routing ambiguous for question: {arbitration['scores']}"
            log_entry["execution_time"] = round(time.time() - start_time, 3)
            log_entry["timing"] = timing
            _log_query(log_entry)
            return log_entry

        final_domain = arbitration["selected_domain"]
        final_resources = _ensure_domain_resources(final_domain)
        final_tables = table_rankings[final_domain]["selected_tables"]
        final_ranked_intents = intent_rankings[final_domain]["ranked_intents"]
        intent = dict(final_ranked_intents[0]) if final_ranked_intents else None
        if intent:
            intent.pop("_score", None)
            intent.pop("_normalized_score", None)

        log_entry["domain"] = final_domain
        log_entry["tables"] = final_tables
        logger.info(
            f"[Step 2] Selected domain={final_domain}, "
            f"tables={final_tables} ({timing['intent_detection']}s)"
        )

        # ─── Cache check (after final domain resolved) ──────
        cached = get_cached_result(question, final_domain)
        if cached:
            cached.update({
                "question": question,
                "domain": final_domain,
                "candidate_domains": candidate_domains,
                "domain_routing": log_entry["domain_routing"],
                "domain_tables": log_entry["domain_tables"],
                "execution_time": round(time.time() - start_time, 3),
                "timing": timing,
            })
            logger.info("[Pipeline] Cache HIT → returning cached SQL")
            return cached

        schema_desc = get_schema_description(final_resources["profiles"], final_tables)
        log_entry["debug"]["schema_description"] = schema_desc

        if intent:
            log_entry["intent"] = intent.get("intent_id")
            log_entry["intent_name"] = intent.get("intent_name", "")
            log_entry["intent_description"] = intent.get("description", "")
            log_entry["intent_sql_template"] = intent.get("sql_template", "")

        # ─── Step 3: Entity Extraction ──────────────────────
        t0 = time.time()
        logger.info("[Step 3] Entity Extraction")
        raw_entities = extract_entities_local(question, domain_id=domain_id)
        entities = normalize_entities(raw_entities)
        # Inject user context: "tôi" / "của tôi" / "của mình" → current user
        if user_context and not entities.get("employee_id") and not entities.get("employee_name"):
            _q = question.lower()
            _self_keywords = ["tôi", "của tôi", "của mình", "cho tôi", "cho mình", "toi", "cua toi"]
            if any(kw in _q for kw in _self_keywords):
                if user_context.get("employee_id"):
                    entities["employee_id"] = user_context["employee_id"]
                if user_context.get("employee_name"):
                    entities["employee_name"] = user_context["employee_name"]
                logger.info(f"[Step 3] Injected user context: {user_context.get('employee_id')}")

        log_entry["entities"] = entities
        timing["entity_extraction"] = round(time.time() - t0, 3)
        logger.info(f"[Step 3] Entities: {entities} ({timing['entity_extraction']}s)")

        # ─── Step 4: Template Retrieval + Slot Filling ──────
        t0 = time.time()
        logger.info("[Step 4] Template Retrieval")
        template_sql = ""
        filled_template = ""
        unfilled = {}
        template_complete = False

        if intent:
            template_sql = get_template_for_intent(intent, final_resources["approved_templates"]) or ""
            log_entry["debug"]["template_sql"] = template_sql
            if template_sql and entities:
                filled_template, unfilled = fill_template(template_sql, entities)
                template_complete = len(unfilled) == 0
                logger.info(
                    f"[Step 4] Template complete: {template_complete} "
                    f"(unfilled: {list(unfilled.keys())})"
                )
            else:
                filled_template = template_sql

        timing["template_fill"] = round(time.time() - t0, 3)
        logger.info(f"[Step 4] ({timing['template_fill']}s)")

        # ─── Step 5: SQL Generation ─────────────────────────
        t0 = time.time()
        if template_complete and filled_template:
            logger.info("[Step 5] Template-fill complete → skip LLM")
            sql = filled_template
            log_entry["model_info"] = {
                **get_generation_config(),
                "active_model": "template-first",
                "active_backend": "template",
                "used_fallback": False,
                "error": "",
            }
        else:
            logger.info("[Step 5] SQL Generation (LLM)")
            prompt = build_sql_prompt(
                question=question,
                schema_description=schema_desc,
                domain_name=final_resources["config"].get("display_name", final_domain),
                intent_name=intent.get("intent_id", "") if intent else "",
                intent_description=intent.get("description", "") if intent else "",
                entities=entities,
                template_sql=template_sql,
                row_limit=QUERY_ROW_LIMIT,
            )
            log_entry["debug"]["prompt"] = prompt
            sql, model_info = _generate_sql_with_demo_fallback(
                prompt=prompt,
                demo_mode=demo_mode,
                table_names=final_tables,
                template_sql=template_sql,
            )
            log_entry["model_info"] = model_info

        sql = inject_test_account(sql)
        log_entry["sql"] = sql
        timing["sql_generation"] = round(time.time() - t0, 3)
        logger.info(f"[Step 5] ({timing['sql_generation']}s)")

        # ─── Step 6: Validation + Semantic Check + Retry ───
        t0 = time.time()
        logger.info("[Step 6] Validation")
        retry = RetryHandler(max_retries=MAX_RETRY_ATTEMPTS)

        profiles = final_resources["profiles"]
        db_config = final_resources["db_config"]

        is_valid, error_msg, error_type = validate_all(sql, profiles)
        log_entry["validator"] = "PASS" if is_valid else "FAIL"

        while not is_valid and retry.should_retry(error_type):
            logger.warning(f"[Step 6] Validation failed ({error_type}): {error_msg}")

            if retry.should_attempt_repair(error_type):
                logger.info("[Step 6] Attempting SQL repair...")
                repair_ok, repaired_sql = retry.attempt_repair(sql, error_msg, question, entities, error_type)
                if repair_ok:
                    sql = repaired_sql
                    log_entry["sql"] = sql
                    is_valid, error_msg, error_type = validate_all(sql, profiles)
                    if is_valid:
                        logger.info("[Step 6] SQL repair successful!")
                        log_entry["validator"] = "PASS"
                        break

            if retry.should_regenerate():
                logger.info(f"[Step 6] Retry #{retry.retry_count + 1} - regenerating SQL")
                retry.record_attempt(sql, error_msg, error_type)

                # When SQL is empty or not real SQL, re-send full generation prompt
                # instead of "fix this SQL" prompt (which confuses Qwen3.5)
                _has_sql = sql and sql.strip() and any(
                    kw in sql.upper() for kw in ["SELECT", "FROM", "WHERE"]
                )
                if _has_sql:
                    retry_prompt = retry.get_retry_prompt(
                        error_type=error_type,
                        sql=sql,
                        error_message=error_msg,
                        schema=schema_desc,
                        question=question,
                    )
                else:
                    logger.info("[Step 6] SQL empty/invalid → re-sending full generation prompt")
                    retry_prompt = build_sql_prompt(
                        question=question,
                        schema_description=schema_desc,
                        domain_name=final_resources["config"].get("display_name", final_domain),
                        intent_name=intent.get("intent_id", "") if intent else "",
                        intent_description=intent.get("description", "") if intent else "",
                        entities=entities,
                        template_sql=template_sql,
                        row_limit=QUERY_ROW_LIMIT,
                    )

                sql, log_entry["model_info"] = _generate_sql_with_demo_fallback(
                    prompt=retry_prompt,
                    demo_mode=demo_mode,
                    table_names=final_tables,
                    template_sql=template_sql,
                )
                log_entry["sql"] = sql
                is_valid, error_msg, error_type = validate_all(sql, profiles)
                log_entry["validator"] = "PASS" if is_valid else "FAIL"
            else:
                break

        if not is_valid:
            log_entry["error"] = f"Validation failed after {retry.retry_count} retries: {error_msg}"
            log_entry["retry_count"] = retry.retry_count
            log_entry["execution_time"] = round(time.time() - start_time, 3)
            log_entry["timing"] = timing
            log_entry["confidence"] = compute_confidence(
                sql_executed=False,
                entity_valid=True,
                schema_valid=False,
                row_count=0,
                semantic_ok=False,
                structure_score=0.0,
            )
            _log_query(log_entry)
            return log_entry

        semantic_ok, semantic_warnings = validate_semantic(question, sql)
        log_entry["semantic_warnings"] = semantic_warnings

        if not semantic_ok and retry.should_retry("semantic"):
            logger.warning(f"[Step 6] Semantic issues: {semantic_warnings}")

            if retry.should_attempt_repair("semantic"):
                logger.info("[Step 6] Attempting semantic repair...")
                repair_ok, repaired_sql = retry.attempt_repair(
                    sql,
                    "; ".join(semantic_warnings),
                    question,
                    entities,
                    "semantic",
                )
                if repair_ok:
                    sql = repaired_sql
                    log_entry["sql"] = sql
                    semantic_ok, semantic_warnings = validate_semantic(question, sql)
                    log_entry["semantic_warnings"] = semantic_warnings
                    if semantic_ok:
                        logger.info("[Step 6] Semantic repair successful!")

            if not semantic_ok and retry.should_regenerate():
                logger.info(f"[Step 6] Retry #{retry.retry_count + 1} - regenerating for semantic fix")
                retry.record_attempt(sql, "; ".join(semantic_warnings), "semantic")

                _has_sql = sql and sql.strip() and any(
                    kw in sql.upper() for kw in ["SELECT", "FROM", "WHERE"]
                )
                if _has_sql:
                    retry_prompt = retry.get_retry_prompt(
                        error_type="semantic",
                        sql=sql,
                        error_message="; ".join(semantic_warnings),
                        schema=schema_desc,
                        question=question,
                        semantic_warnings=semantic_warnings,
                    )
                else:
                    logger.info("[Step 6] SQL empty/invalid → re-sending full generation prompt (semantic)")
                    retry_prompt = build_sql_prompt(
                        question=question,
                        schema_description=schema_desc,
                        domain_name=final_resources["config"].get("display_name", final_domain),
                        intent_name=intent.get("intent_id", "") if intent else "",
                        intent_description=intent.get("description", "") if intent else "",
                        entities=entities,
                        template_sql=template_sql,
                        row_limit=QUERY_ROW_LIMIT,
                    )

                sql, log_entry["model_info"] = _generate_sql_with_demo_fallback(
                    prompt=retry_prompt,
                    demo_mode=demo_mode,
                    table_names=final_tables,
                    template_sql=template_sql,
                )
                log_entry["sql"] = sql
                semantic_ok, semantic_warnings = validate_semantic(question, sql)
                log_entry["semantic_warnings"] = semantic_warnings

        explain_ok, explain_err = (True, "") if demo_mode else explain_query(sql, db_config=db_config)
        if not explain_ok and retry.should_retry("syntax"):
            logger.warning(f"[Step 6] EXPLAIN failed: {explain_err}")

            if retry.should_attempt_repair("syntax"):
                logger.info("[Step 6] Attempting syntax repair...")
                repair_ok, repaired_sql = retry.attempt_repair(sql, explain_err, question, entities, "syntax")
                if repair_ok:
                    sql = repaired_sql
                    log_entry["sql"] = sql
                    explain_ok, explain_err = explain_query(sql, db_config=db_config)
                    if explain_ok:
                        logger.info("[Step 6] Syntax repair successful!")

            if not explain_ok and retry.should_regenerate():
                logger.info("[Step 6] Regenerating SQL for EXPLAIN fix...")
                retry.record_attempt(sql, explain_err, "syntax")

                _has_sql = sql and sql.strip() and any(
                    kw in sql.upper() for kw in ["SELECT", "FROM", "WHERE"]
                )
                if _has_sql:
                    retry_prompt = retry.get_retry_prompt(
                        error_type="syntax",
                        sql=sql,
                        error_message=f"EXPLAIN failed: {explain_err}",
                        schema=schema_desc,
                        question=question,
                    )
                else:
                    logger.info("[Step 6] SQL empty/invalid → re-sending full generation prompt (EXPLAIN)")
                    retry_prompt = build_sql_prompt(
                        question=question,
                        schema_description=schema_desc,
                        domain_name=final_resources["config"].get("display_name", final_domain),
                        intent_name=intent.get("intent_id", "") if intent else "",
                        intent_description=intent.get("description", "") if intent else "",
                        entities=entities,
                        template_sql=template_sql,
                        row_limit=QUERY_ROW_LIMIT,
                    )

                sql, log_entry["model_info"] = _generate_sql_with_demo_fallback(
                    prompt=retry_prompt,
                    demo_mode=demo_mode,
                    table_names=final_tables,
                    template_sql=template_sql,
                )
                log_entry["sql"] = sql
                explain_ok, explain_err = explain_query(sql, db_config=db_config)

        if not explain_ok:
            log_entry["error"] = f"EXPLAIN failed: {explain_err}"
            log_entry["validator"] = "FAIL"
            log_entry["retry_count"] = retry.retry_count
            log_entry["execution_time"] = round(time.time() - start_time, 3)
            log_entry["timing"] = timing
            log_entry["confidence"] = compute_confidence(
                sql_executed=False,
                entity_valid=True,
                schema_valid=True,
                row_count=0,
                semantic_ok=semantic_ok,
                structure_score=0.0,
            )
            _log_query(log_entry)
            return log_entry

        log_entry["retry_count"] = retry.retry_count
        timing["validation"] = round(time.time() - t0, 3)
        logger.info(f"[Step 6] ({timing['validation']}s)")

        # ─── Step 7: Execute on DB + Smart Result Handling ─
        t0 = time.time()
        logger.info("[Step 7] Execute on DB")
        if demo_mode:
            success = True
            rows = get_demo_rows(
                domain_id=final_domain,
                question=question,
                sql=sql,
                intent_name=intent.get("intent_name", "") if intent else "",
                table_names=final_tables,
            )
            db_error = ""
        else:
            success, rows, db_error = execute_query(sql, db_config=db_config)

        if not success:
            exec_error_type = classify_execution_error(db_error)
            logger.warning(f"[Step 7] DB error ({exec_error_type}): {db_error}")

            if exec_error_type in ("syntax", "runtime") and retry.should_retry(exec_error_type):
                if retry.should_attempt_repair(exec_error_type):
                    logger.info(f"[Step 7] Attempting {exec_error_type} repair...")
                    repair_ok, repaired_sql = retry.attempt_repair(sql, db_error, question, entities, exec_error_type)
                    if repair_ok:
                        sql = repaired_sql
                        log_entry["sql"] = sql
                        success, rows, db_error = execute_query(sql, db_config=db_config)
                        log_entry["rows"] = len(rows) if rows else 0
                        if success:
                            logger.info(f"[Step 7] {exec_error_type} repair successful!")

                if not success and retry.should_regenerate():
                    logger.info(f"[Step 7] Regenerating SQL for {exec_error_type} fix...")
                    retry.record_attempt(sql, db_error, exec_error_type)
                    retry_prompt = retry.get_retry_prompt(
                        error_type=exec_error_type,
                        sql=sql,
                        error_message=db_error,
                        schema=schema_desc,
                        question=question,
                    )
                    sql, log_entry["model_info"] = _generate_sql_with_demo_fallback(
                        prompt=retry_prompt,
                        demo_mode=demo_mode,
                        table_names=final_tables,
                        template_sql=template_sql,
                    )
                    log_entry["sql"] = sql
                    log_entry["retry_count"] = retry.retry_count

                    is_valid, _, _ = validate_all(sql, profiles)
                    if is_valid:
                        success, rows, db_error = execute_query(sql, db_config=db_config)
                        log_entry["rows"] = len(rows) if rows else 0

            if not success:
                log_entry["error"] = f"DB execution failed ({exec_error_type}): {db_error}"
                log_entry["execution_time"] = round(time.time() - start_time, 3)
                log_entry["timing"] = timing
                log_entry["confidence"] = compute_confidence(
                    sql_executed=False,
                    entity_valid=True,
                    schema_valid=True,
                    row_count=0,
                    semantic_ok=semantic_ok,
                    structure_score=0.0,
                )
                _log_query(log_entry)
                return log_entry

        row_count = len(rows) if rows else 0
        log_entry["rows"] = row_count

        struct_valid, struct_issues, struct_score = validate_sql_structure(
            sql=sql,
            question=question,
            entities=entities,
            profiles=profiles,
            intent=intent,
        )
        log_entry["structure_score"] = struct_score
        log_entry["structure_issues"] = struct_issues

        entity_valid = True
        if row_count == 0 and success:
            if struct_valid:
                log_entry["validator"] = "PASS_EMPTY"
                logger.info(f"[Step 7] PASS_EMPTY: SQL structure OK (score={struct_score}), data rỗng")
            else:
                logger.info("[Step 7] row=0 + structure issues → running data validation...")
                data_result = validate_empty_result(
                    sql=sql,
                    entities=entities,
                    profiles=profiles,
                    executor_fn=lambda check_sql, params=None, row_limit=1, timeout=None: execute_query(
                        check_sql,
                        params=params,
                        row_limit=row_limit,
                        timeout=timeout or 5,
                        db_config=db_config,
                    ),
                    domain_context=final_resources["config"],
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

        log_entry["confidence"] = compute_confidence(
            sql_executed=success,
            entity_valid=entity_valid,
            schema_valid=True,
            row_count=row_count,
            semantic_ok=semantic_ok,
            structure_score=struct_score,
        )

        timing["execution"] = round(time.time() - t0, 3)
        logger.info(f"[Step 7] ({timing['execution']}s)")

        if intent and rows and row_count > 0:
            intent_id = intent.get("intent_id", "")
            if intent_id:
                # When template was filled via slot-fill, save the parameterized
                # template (with {placeholders}) not the filled SQL, so future
                # queries with different values can reuse it correctly.
                sql_to_save = template_sql if template_complete and template_sql else sql
                save_approved_template(
                    intent_id,
                    sql_to_save,
                    path=final_resources["paths"].get("approved_templates_dir"),
                    domain_id=final_domain,
                )
                final_resources["approved_templates"][intent_id] = sql_to_save

        # ─── Step 8: Result Formatting + Explain ───────────
        if explain:
            t0 = time.time()
            logger.info("[Step 8] Explain & Format")
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
            logger.info("[Step 8] Explain skipped (--no-explain)")

        if rows:
            log_entry["result_table"] = format_result_table(rows)
            log_entry["result_data"] = rows

        log_entry["debug"].update({
            "domain": final_domain,
            "tables": final_tables,
            "intent": log_entry.get("intent"),
            "intent_name": log_entry.get("intent_name"),
            "intent_description": log_entry.get("intent_description"),
            "entities": entities,
            "candidate_domains": candidate_domains,
            "domain_routing": log_entry.get("domain_routing"),
            "timing": timing,
            "model_info": log_entry.get("model_info", {}),
        })
        log_entry["execution_time"] = round(time.time() - start_time, 3)
        log_entry["timing"] = timing
        _log_query(log_entry)
        cache_result(question, log_entry, domain_id=final_domain)

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
    logger.info("[Timing] ─── Step Breakdown ───")
    for step, elapsed in timing.items():
        logger.info(f"  {step:20s} {elapsed:6.3f}s")
    total = sum(timing.values())
    logger.info(f"  {'TOTAL':20s} {total:6.3f}s")


def _get_queries_log_file() -> str:
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
    log_file = _get_queries_log_file()

    log_record = {
        "question": entry.get("question"),
        "domain": entry.get("domain"),
        "candidate_domains": entry.get("candidate_domains", []),
        "domain_routing": entry.get("domain_routing", {}),
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
