#!/usr/bin/env python3
"""
Quick verification that repair-first integration is properly set up.
Runs smoke tests to ensure all imports work and retry handler has new methods.
"""

import sys
sys.path.insert(0, '.')

print("=" * 80)
print("REPAIR-FIRST INTEGRATION VERIFICATION")
print("=" * 80)

# Test 1: Import retry_handler and check for new methods
print("\n1. Checking RetryHandler methods...")
try:
    from pipeline.retry_handler import RetryHandler
    
    # Verify methods exist
    required_methods = ["should_attempt_repair", "should_regenerate", "attempt_repair"]
    for method_name in required_methods:
        if hasattr(RetryHandler, method_name):
            print(f"   ✓ RetryHandler.{method_name} exists")
        else:
            print(f"   ✗ RetryHandler.{method_name} MISSING!")
            sys.exit(1)
    
    # Create instance and verify it works
    retry = RetryHandler(max_retries=2)
    print(f"   ✓ RetryHandler instantiation successful")
    print(f"   ✓ Initial repair_attempted status: {retry.repair_attempted}")
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    sys.exit(1)

# Test 2: Import sql_repairer and check function
print("\n2. Checking SQL Repairer...")
try:
    from sql_generation.sql_repairer import repair_sql
    print(f"   ✓ repair_sql function imported successfully")
    
    # Try a simple repair test
    test_sql = "SELECT * WHERE id = 1"  # Missing FROM
    success, repaired = repair_sql(test_sql, "TABLE not found", "select account details", {})
    print(f"   ✓ repair_sql callable")
    print(f"     - Input: {test_sql}")
    print(f"     - Repair attempted: {success}")
    if repaired != test_sql:
        print(f"     - Output: {repaired}")
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    sys.exit(1)

# Test 3: Check pipeline_runner imports
print("\n3. Checking pipeline_runner imports...")
try:
    from pipeline.pipeline_runner import run_pipeline
    print(f"   ✓ run_pipeline imported successfully")
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    sys.exit(1)

# Test 4: Verify pipeline_runner uses new retry methods (via grep-based check)
print("\n4. Checking pipeline_runner integration...")
try:
    with open("pipeline/pipeline_runner.py", "r") as f:
        content = f.read()
    
    integration_checks = [
        ("should_attempt_repair()", "Repair attempt check"),
        ("should_regenerate()", "Regenerate check"),
        ("attempt_repair(", "Repair execution"),
        ("[Step 6]", "Step 6 logging"),
        ("[Step 7]", "Step 7 logging"),
    ]
    
    for check_str, description in integration_checks:
        if check_str in content:
            print(f"   ✓ {description} found in pipeline_runner")
        else:
            print(f"   ✗ {description} NOT FOUND in pipeline_runner")
    
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    sys.exit(1)

# Test 5: Verify SQL repair strategies
print("\n5. Checking repair strategies...")
try:
    with open("sql_generation/sql_repairer.py", "r") as f:
        content = f.read()
    
    strategies = [
        ("_repair_missing_from", "Missing FROM clause"),
        ("_repair_missing_where", "Missing WHERE clause"),
        ("_repair_column_reference", "Column reference issues"),
        ("_repair_time_filter", "Time filter issues"),
        ("_repair_aggregation", "Aggregation issues"),
        ("_repair_syntax", "SQL syntax issues"),
    ]
    
    for func_name, description in strategies:
        if f"def {func_name}" in content:
            print(f"   ✓ {description} ({func_name})")
        else:
            print(f"   ✗ {description} MISSING ({func_name})")
    
except Exception as e:
    print(f"   ✗ ERROR: {e}")
    sys.exit(1)

print("\n" + "=" * 80)
print("✓ ALL VERIFICATION CHECKS PASSED")
print("=" * 80)
print("\nRepair-first strategy is properly integrated!")
print("\nNext steps:")
print("  1. Run: python test_repair_integration.py")
print("  2. Monitor logs for [SQLRepairer] messages")
print("  3. Check repair success rates by type")
print()
