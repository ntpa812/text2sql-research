import sys
import os
import json
import argparse
import logging

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def print_result(result: dict, show_timing: bool = True):
    """In kết quả pipeline ra console theo format chuẩn."""
    print(f"\nUser Question: {result.get('question', '')}")
    print(f"→ Domain: {result.get('domain', 'N/A')}")
    if result.get("candidate_domains"):
        print(f"→ Candidate Domains: {result.get('candidate_domains', [])}")
    print(f"→ Tables: {result.get('tables', [])}")
    print(f"→ Intent: {result.get('intent', 'N/A')}")
    print(f"→ Entities: {result.get('entities', {})}")
    print(f"→ SQL: {result.get('sql', 'N/A')}")

    validator = result.get("validator", "N/A")
    print(f"→ Validator: {validator}")

    if result.get("semantic_warnings"):
        for w in result["semantic_warnings"]:
            print(f"  ⚠ {w}")

    if result.get("domain_routing", {}).get("arbitration_reason"):
        print(f"→ Domain Routing: {result['domain_routing']['arbitration_reason']}")

    if result.get("error"):
        print(f"→ Error: {result['error']}")
    elif validator == "PASS_EMPTY":
        print(f"→ Result: 0 rows (dữ liệu không tồn tại, SQL hợp lệ)")
    elif validator == "DATA_ERROR":
        dv = result.get("data_validation", {})
        print(f"→ Result: DATA_ERROR — {dv.get('message', '')}")
    else:
        print(f"→ Result: {result.get('rows', 0)} rows")

    # Confidence score
    conf = result.get("confidence", {})
    if conf:
        score = conf.get("score", 0)
        passed = conf.get("passed", False)
        print(f"→ Confidence: {score} ({'PASS' if passed else 'LOW'})")

    # Structure score
    struct_score = result.get("structure_score")
    if struct_score is not None:
        print(f"→ Structure: {struct_score}")
        issues = result.get("structure_issues", [])
        for issue in issues:
            print(f"  ⚠ {issue}")

    # Cache hit
    if result.get("cache_hit"):
        print(f"→ Cache: HIT (skip pipeline)")

    if result.get("explain"):
        print(f"→ Explain: {result['explain']}")

    if show_timing and result.get("timing"):
        timing = result["timing"]
        parts = [f"{k}={v}s" for k, v in timing.items()]
        print(f"→ Timing: {', '.join(parts)} | total={result.get('execution_time', 0):.2f}s")


def run_batch(file_path: str, no_explain: bool = False, parallel: int = 1, forced_domain: str | None = None):
    """Chạy pipeline cho tất cả câu hỏi từ file (json/csv/xlsx/md)."""
    import time
    from pipeline.pipeline_runner import run_pipeline
    from dataset_loader.question_loader import load_questions, save_processed

    print(f"\n{'='*60}")
    print(f"  Batch Mode — {os.path.basename(file_path)}")
    print(f"  explain={'OFF' if no_explain else 'ON'} | parallel={parallel}")
    print(f"{'='*60}")

    questions = load_questions(file_path)
    print(f"Loaded {len(questions)} questions\n")

    # Save processed version
    processed_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "data", "user_questions", "processed",
    )
    processed_path = os.path.join(processed_dir, "questions.json")
    save_processed(questions, processed_path)

    batch_start = time.time()

    # Run pipeline
    def _run_one(q_item):
        return run_pipeline(q_item["question"], explain=not no_explain, forced_domain=forced_domain)

    if parallel > 1:
        from concurrent.futures import ThreadPoolExecutor
        print(f"Running {len(questions)} queries with {parallel} threads...\n")
        with ThreadPoolExecutor(max_workers=parallel) as ex:
            all_results = list(ex.map(_run_one, questions))
        for i, result in enumerate(all_results, 1):
            print(f"\n{'─'*60}")
            print(f"[{i}/{len(questions)}]")
            print_result(result)
    else:
        all_results = []
        for i, q_item in enumerate(questions, 1):
            print(f"\n{'─'*60}")
            print(f"[{i}/{len(questions)}] Processing...")
            print(f"{'─'*60}")
            result = _run_one(q_item)
            all_results.append(result)
            print_result(result)

    batch_elapsed = round(time.time() - batch_start, 2)

    # Summary
    total = len(all_results)
    passed = sum(1 for r in all_results if r.get("validator") == "PASS")
    pass_empty = sum(1 for r in all_results if r.get("validator") == "PASS_EMPTY")
    data_errors = sum(1 for r in all_results if r.get("validator") == "DATA_ERROR")
    failed = sum(1 for r in all_results if r.get("error") and r.get("validator") not in ("PASS_EMPTY", "DATA_ERROR"))
    cache_hits = sum(1 for r in all_results if r.get("cache_hit"))
    avg_time = round(batch_elapsed / total, 2) if total else 0
    avg_conf = round(sum(r.get("confidence", {}).get("score", 0) for r in all_results) / total, 2) if total else 0
    print(f"\n{'='*60}")
    print(f"  SUMMARY: {total} queries | {passed} PASS | {pass_empty} EMPTY | {data_errors} DATA_ERR | {failed} FAIL")
    if cache_hits:
        print(f"  Cache hits: {cache_hits}/{total}")
    print(f"  Avg confidence: {avg_conf} | Total: {batch_elapsed}s | Avg: {avg_time}s/query")
    print(f"{'='*60}")

    # Save batch results to JSON
    from datetime import datetime
    batch_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "batch_result")
    os.makedirs(batch_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    batch_file = os.path.join(batch_dir, f"{ts}.json")

    batch_output = []
    for r in all_results:
        entry = {
            "question": r.get("question"),
            "domain": r.get("domain"),
            "candidate_domains": r.get("candidate_domains", []),
            "tables": r.get("tables", []),
            "intent": r.get("intent"),
            "entities": r.get("entities", {}),
            "sql": r.get("sql"),
            "validator": r.get("validator"),
            "rows": r.get("rows", 0),
            "confidence": r.get("confidence", {}),
            "timing": r.get("timing", {}),
        }
        if r.get("semantic_warnings"):
            entry["semantic_warnings"] = r["semantic_warnings"]
        if r.get("data_validation"):
            entry["data_validation"] = r["data_validation"]
        if r.get("error"):
            entry["error"] = r["error"]
        batch_output.append(entry)

    with open(batch_file, "w", encoding="utf-8") as f:
        json.dump(batch_output, f, ensure_ascii=False, indent=2)

    print(f"\nBatch results saved to: {batch_file}")


def run_interactive(no_explain: bool = False, forced_domain: str | None = None):
    """Chế độ hỏi đáp tương tác."""
    from pipeline.pipeline_runner import run_pipeline

    print(f"\n{'='*60}")
    print("  Banking Text2SQL Pipeline — Interactive Mode")
    print(f"  explain={'OFF' if no_explain else 'ON'}")
    print(f"{'='*60}")

    while True:
        print()
        question = input("User Question (hoặc 'quit' để thoát): ").strip()

        if not question or question.lower() in ("quit", "exit", "q"):
            print("Tạm biệt!")
            break

        result = run_pipeline(question, explain=not no_explain, forced_domain=forced_domain)
        print_result(result)


def main():
    parser = argparse.ArgumentParser(description="Banking Text2SQL Pipeline")
    parser.add_argument("file", nargs="?", help="Input file (json/csv/xlsx/md) for batch mode")
    parser.add_argument("--no-explain", action="store_true", help="Skip explain step (faster)")
    parser.add_argument("--parallel", type=int, default=1, help="Number of parallel threads (batch mode)")
    parser.add_argument("--warm", action="store_true", help="Warm up configured LLM backend before running")
    parser.add_argument("--test-mode", action="store_true", help="Enable test mode (inject mock account)")
    parser.add_argument("--clear-cache", action="store_true", help="Xoá query cache trước khi chạy")
    parser.add_argument("--domain", help="Force a specific domain id (debug/test)")
    args = parser.parse_args()

    # Test mode: inject mock account
    if args.test_mode:
        import config.settings as cfg
        cfg.TEST_MODE = True
        print("⚡ TEST MODE enabled — mock account will be injected")

    # Clear cache if requested
    if args.clear_cache:
        from pipeline.query_cache import clear_query_cache
        clear_query_cache()
        print("🗑 Query cache cleared")

    if args.warm:
        from sql_generation.llm_sql_generator import warm_ollama, warm_openai_compatible
        warm_openai_compatible()
        warm_ollama()

    if args.file:
        file_path = args.file
        if not os.path.isabs(file_path):
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
        run_batch(
            file_path,
            no_explain=args.no_explain,
            parallel=args.parallel,
            forced_domain=args.domain,
        )
    else:
        run_interactive(no_explain=args.no_explain, forced_domain=args.domain)


if __name__ == "__main__":
    main()
