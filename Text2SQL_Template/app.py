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
    print(f"→ Tables: {result.get('tables', [])}")
    print(f"→ Intent: {result.get('intent', 'N/A')}")
    print(f"→ Entities: {result.get('entities', {})}")
    print(f"→ SQL: {result.get('sql', 'N/A')}")
    print(f"→ Validator: {result.get('validator', 'N/A')}")

    if result.get("error"):
        print(f"→ Error: {result['error']}")
    else:
        print(f"→ Result: {result.get('rows', 0)} rows")

    if result.get("explain"):
        print(f"→ Explain: {result['explain']}")

    if show_timing and result.get("timing"):
        timing = result["timing"]
        parts = [f"{k}={v}s" for k, v in timing.items()]
        print(f"→ Timing: {', '.join(parts)} | total={result.get('execution_time', 0):.2f}s")


def run_batch(file_path: str, no_explain: bool = False, parallel: int = 1):
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
        return run_pipeline(q_item["question"], explain=not no_explain)

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
    failed = sum(1 for r in all_results if r.get("error"))
    avg_time = round(batch_elapsed / total, 2) if total else 0
    print(f"\n{'='*60}")
    print(f"  SUMMARY: {total} questions | {passed} PASS | {failed} errors")
    print(f"  Total: {batch_elapsed}s | Avg: {avg_time}s/query")
    print(f"{'='*60}")

    # Save batch results to JSON
    from datetime import datetime
    batch_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "batch_result")
    os.makedirs(batch_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    batch_file = os.path.join(batch_dir, f"{ts}.json")

    batch_output = []
    for r in all_results:
        batch_output.append({
            "question": r.get("question"),
            "tables": r.get("tables", []),
            "intent": r.get("intent"),
            "entities": r.get("entities", {}),
            "sql": r.get("sql"),
            "validator": r.get("validator"),
            "rows": r.get("rows", 0),
            "timing": r.get("timing", {}),
        })

    with open(batch_file, "w", encoding="utf-8") as f:
        json.dump(batch_output, f, ensure_ascii=False, indent=2)

    print(f"\nBatch results saved to: {batch_file}")


def run_interactive(no_explain: bool = False):
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

        result = run_pipeline(question, explain=not no_explain)
        print_result(result)


def main():
    parser = argparse.ArgumentParser(description="Banking Text2SQL Pipeline")
    parser.add_argument("file", nargs="?", help="Input file (json/csv/xlsx/md) for batch mode")
    parser.add_argument("--no-explain", action="store_true", help="Skip explain step (faster)")
    parser.add_argument("--parallel", type=int, default=1, help="Number of parallel threads (batch mode)")
    parser.add_argument("--warm", action="store_true", help="Warm up Ollama model before running")
    args = parser.parse_args()

    if args.warm:
        from sql_generation.llm_sql_generator import warm_ollama
        warm_ollama()

    if args.file:
        file_path = args.file
        if not os.path.isabs(file_path):
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
        run_batch(file_path, no_explain=args.no_explain, parallel=args.parallel)
    else:
        run_interactive(no_explain=args.no_explain)


if __name__ == "__main__":
    main()
