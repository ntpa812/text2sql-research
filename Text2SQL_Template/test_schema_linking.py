"""
Test Schema Linking Optimization
So sánh schema size khi dùng all tables vs selected tables
"""

from schema_router.schema_loader import load_all_profiles, get_schema_description
from schema_router.table_selector import select_tables

# Load all profiles
profiles = load_all_profiles()

# Test questions
test_questions = [
    "Tra cứu giao dịch chuyển tiền tới số tài khoản 123 trong tháng 1",
    "Xem tất cả thông tin khách hàng của tài khoản 456",
    "Cho tôi xem các giao dịch nhận tiền của tài khoản 456 trong tuần này",
]

print("=" * 70)
print("SCHEMA LINKING OPTIMIZATION TEST")
print("=" * 70)

for question in test_questions:
    print(f"\nQuestion: {question}")
    
    # Get full schema
    full_schema = get_schema_description(profiles)
    full_size = len(full_schema)
    
    # Get selected tables
    selected_tables = select_tables(question, profiles, use_embedding=False)
    optimized_schema = get_schema_description(profiles, selected_tables)
    optimized_size = len(optimized_schema)
    
    # Calculate savings
    savings = full_size - optimized_size
    savings_pct = (savings / full_size * 100) if full_size > 0 else 0
    
    print(f"  Selected tables: {selected_tables}")
    print(f"  Full schema size:      {full_size:>6} chars")
    print(f"  Optimized schema size: {optimized_size:>6} chars")
    print(f"  Savings:               {savings:>6} chars ({savings_pct:.1f}%)")
    print(f"  Optimized schema:\n{optimized_schema[:200]}...")

print("\n" + "=" * 70)
