"""
Test repair-first strategy integration across all validation points.
Monitors repair attempts vs regeneration attempts across structure, semantic, and DB execution.
"""

import json
import time
import sys
import logging
from collections import defaultdict

# Add parent dir to path
sys.path.insert(0, '.')

from pipeline.pipeline_runner import run_pipeline

# Configure logging to capture [SQLRepairer] and retry messages
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s'
)

def test_repair_integration(test_file: str = "data/user_questions/test_sets/banking_basic.json"):
    """
    Run batch test and collect repair/regeneration statistics.
    
    Args:
        test_file: Path to test question file
    """
    print(f"\n{'='*80}")
    print(f"Testing Repair-First Strategy Integration")
    print(f"{'='*80}\n")
    
    # Load test questions
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
    except FileNotFoundError:
        print(f"ERROR: Test file not found: {test_file}")
        return
    
    # Statistics
    stats = {
        "total": 0,
        "success": 0,
        "failed": 0,
        "repair_attempted": defaultdict(int),
        "repair_successful": defaultdict(int),
        "regenerate_attempted": defaultdict(int),
        "regenerate_successful": defaultdict(int),
        "retry_types": defaultdict(int),
    }
    
    questions = test_data if isinstance(test_data, list) else test_data.get("questions", [])
    
    print(f"Running {len(questions)} test questions...\n")
    
    # Capture logs to track repairs
    repair_log = []
    original_handlers = logging.root.handlers[:]
    
    class LogCapture(logging.Handler):
        def emit(self, record):
            msg = record.getMessage()
            if "[SQLRepairer]" in msg or "repair" in msg.lower()[:100] or "regenerat" in msg.lower()[:100]:
                repair_log.append((record.levelname, msg))
    
    log_capture = LogCapture()
    logging.root.addHandler(log_capture)
    
    for idx, question_data in enumerate(questions, 1):
        if isinstance(question_data, str):
            question = question_data
        else:
            question = question_data.get("question", "")
        
        if not question:
            continue
        
        stats["total"] += 1
        print(f"[{idx}/{len(questions)}] {question[:60]}...")
        
        repair_log.clear()
        start_time = time.time()
        
        try:
            result = run_pipeline(question, use_embedding=False, explain=False)
            elapsed = time.time() - start_time
            
            # Check result - handle both cached and fresh results
            has_sql = result.get("sql") is not None
            has_rows_key = "rows" in result
            is_success = has_sql and (has_rows_key or result.get("cached"))  # cached results might not have rows key
            
            if is_success:
                stats["success"] += 1
                row_count = result.get("rows", 0) if has_rows_key else "(cached)"
                retry_count = result.get("retry_count", 0)
                status = f"✓ SUCCESS ({row_count} rows, {retry_count} retries)"
            else:
                stats["failed"] += 1
                error_msg = result.get("error", "Unknown error")
                if not error_msg or error_msg == "Unknown error":
                    error_msg = f"Missing required fields: sql={has_sql}, rows={has_rows_key}"
                status = f"✗ FAILED: {error_msg[:60]}"
            
            print(f"  {status} ({elapsed:.2f}s)")
            
            # Parse repair/regenerate attempts from logs
            for level, msg in repair_log:
                if "Attempting" in msg and "repair" in msg:
                    repair_type = "structure"
                    if "semantic" in msg:
                        repair_type = "semantic"
                    elif "syntax" in msg:
                        repair_type = "syntax"
                    elif "EXPLAIN" in msg:
                        repair_type = "explain"
                    stats["repair_attempted"][repair_type] += 1
                
                if "repair successful" in msg.lower():
                    repair_type = "structure"
                    if "semantic" in msg:
                        repair_type = "semantic"
                    elif "syntax" in msg:
                        repair_type = "syntax"
                    elif "explain" in msg:
                        repair_type = "explain"
                    stats["repair_successful"][repair_type] += 1
                
                if "Regenerating" in msg or "Retry #" in msg:
                    retry_type = "structure"
                    if "semantic" in msg:
                        retry_type = "semantic"
                    elif "EXPLAIN" in msg or "syntax" in msg:
                        retry_type = "syntax"
                    elif "DB execution" in msg:
                        retry_type = "db_execution"
                    stats["regenerate_attempted"][retry_type] += 1
                    stats["retry_types"][retry_type] += 1
            
        except Exception as e:
            stats["failed"] += 1
            error_detail = f"{type(e).__name__}: {str(e)[:50]}"
            print(f"  ✗ EXCEPTION: {error_detail}")
            repair_log.clear()  # Clear logs on exception
    
    # Remove log capture
    logging.root.removeHandler(log_capture)
    
    # Print summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    print(f"Total Questions: {stats['total']}")
    print(f"Success: {stats['success']} ({100*stats['success']//max(1, stats['total'])}%)")
    print(f"Failed: {stats['failed']} ({100*stats['failed']//max(1, stats['total'])}%)")
    
    print(f"\nRepair Strategy Statistics:")
    total_repairs = sum(stats["repair_attempted"].values())
    total_regenerates = sum(stats["regenerate_attempted"].values())
    
    if total_repairs > 0:
        repair_success_rate = sum(stats["repair_successful"].values()) / total_repairs * 100
        print(f"  Total Repair Attempts: {total_repairs}")
        print(f"  Total Repairs Successful: {sum(stats['repair_successful'].values())} ({repair_success_rate:.1f}%)")
        print(f"  Repairs by Type:")
        for repair_type in sorted(stats["repair_attempted"].keys()):
            attempts = stats["repair_attempted"][repair_type]
            successes = stats["repair_successful"][repair_type]
            success_rate = (successes / attempts * 100) if attempts > 0 else 0
            print(f"    - {repair_type:12} : {attempts:2} attempts, {successes:2} successful ({success_rate:.0f}%)")
    
    if total_regenerates > 0:
        print(f"\n  Total Regenerate Attempts: {total_regenerates}")
        print(f"  Regenerates by Type:")
        for retry_type in sorted(stats["retry_types"].keys()):
            attempts = stats["retry_types"][retry_type]
            print(f"    - {retry_type:15} : {attempts:2} regenerations")
    
    # Calculate efficiency
    if total_repairs > 0 and total_regenerates > 0:
        print(f"\nEfficiency Gain:")
        print(f"  Repairs prevented {total_repairs} expensive regenerations")
        print(f"  Repair-to-Regenerate Ratio: {total_repairs / total_regenerates:.2f}:1")
        print(f"  Estimated Token Savings: ~{total_repairs * 80}ms (vs ~{total_regenerates * 8000}ms regenerations)")
    
    print(f"{'='*80}\n")

if __name__ == "__main__":
    test_file = sys.argv[1] if len(sys.argv) > 1 else "data/user_questions/test_sets/banking_basic.json"
    test_repair_integration(test_file)
