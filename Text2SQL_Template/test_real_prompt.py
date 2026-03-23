"""Test LLM generation with real SQL prompt"""
import sys
sys.path.insert(0, '.')

from sql_generation.llm_sql_generator import generate_sql
from sql_generation.sql_prompt_builder import build_sql_prompt
from schema_router.schema_loader import load_all_profiles, get_schema_description
from schema_router.table_selector import select_tables

question = "Cho tôi xem các giao dịch nhận tiền của tài khoản 456 trong tuần này"

profiles = load_all_profiles()
tables = select_tables(question, profiles, use_embedding=False)
schema_desc = get_schema_description(profiles, tables)

prompt = build_sql_prompt(
    question=question,
    schema_description=schema_desc,
    intent_name="tra_cứu_giao_dịch_tiết_kiệm_theo_tài_khoản_nhận",
    intent_description="Tra cứu giao dịch tiết kiệm theo tài khoản nhận",
    entities={"amount": "456000000"},
    template_sql="",
    row_limit=100,
)

print(f"[TEST] Prompt (first 500 chars):\n{prompt[:500]}")
print(f"\n[TEST] Calling generate_sql()...")

try:
    sql = generate_sql(prompt)
    print(f"[TEST] Generated SQL:\n{sql}")
    print(f"[TEST] SQL length: {len(sql)}")
except Exception as e:
    print(f"[TEST] ERROR: {e}")
    import traceback
    traceback.print_exc()
