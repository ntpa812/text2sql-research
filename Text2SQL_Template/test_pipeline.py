"""Quick test – run pipeline steps one by one."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from schema_router.schema_loader import load_all_profiles, get_schema_description
from schema_router.table_selector import select_tables
from intent_detection.intent_loader import load_intent_dataset, build_intent_index
from intent_detection.intent_ranker import detect_intent
from entity_extraction.ner_local import _regex_fallback, _normalize_ner_output
from slot_filling.entity_normalizer import normalize_entities
from slot_filling.slot_filler import fill_template
from template_store.template_loader import load_approved_templates, get_template_for_intent
from sql_generation.sql_prompt_builder import build_sql_prompt
from sql_generation.llm_sql_generator import generate_sql
from validator.security_guard import validate_all
from config.settings import QUERY_ROW_LIMIT

question = "Tra cứu giao dịch chuyển tiền tới tài khoản 123456789 trong tháng 1"
print(f"Question: {question}")
print("=" * 60)

# Step 1
profiles = load_all_profiles()
tables = select_tables(question, profiles)
schema_desc = get_schema_description(profiles, tables)
print(f"[Step 1] Tables: {tables}")

# Step 2
dataset = load_intent_dataset()
intent_index = build_intent_index(dataset)
intent = detect_intent(question, intent_index)
if intent:
    print(f"[Step 2] Intent ID: {intent.get('intent_id')}")
    print(f"[Step 2] Intent Name: {intent.get('intent_name')}")
    print(f"[Step 2] Description: {intent.get('description', '')[:100]}...")
else:
    print("[Step 2] No intent detected")

# Step 3
raw = _regex_fallback(question)
entities = normalize_entities(_normalize_ner_output(raw))
print(f"[Step 3] Entities: {entities}")

# Step 4
templates = load_approved_templates()
template_sql = get_template_for_intent(intent, templates) if intent else ""
if template_sql:
    print(f"[Step 4] Template: {template_sql[:120]}...")
    filled, unfilled = fill_template(template_sql, entities)
    print(f"[Step 4] Unfilled slots: {list(unfilled.keys())}")
else:
    print("[Step 4] No template found")

# Step 5
prompt = build_sql_prompt(
    question=question,
    schema_description=schema_desc,
    intent_name=intent.get("intent_id", "") if intent else "",
    intent_description=intent.get("description", "") if intent else "",
    entities=entities,
    template_sql=template_sql or "",
    row_limit=QUERY_ROW_LIMIT,
)
print(f"[Step 5] Prompt length: {len(prompt)} chars")
print("[Step 5] Calling Llama 3...")
sql = generate_sql(prompt)
print(f"[Step 5] Generated SQL:\n  {sql}")

# Step 6
is_valid, error_msg, error_type = validate_all(sql, profiles)
print(f"[Step 6] Valid: {is_valid} | Error: {error_msg or 'none'}")

print("=" * 60)
print("DONE - Pipeline test complete")
