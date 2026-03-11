import sys
import os
import json
import logging

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def print_result(result: dict):
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


def run_batch(file_path: str):
    """Chạy pipeline cho tất cả câu hỏi từ file (json/csv/xlsx/md)."""
    from pipeline.pipeline_runner import run_pipeline
    from dataset_loader.question_loader import load_questions, save_processed

    print(f"\n{'='*60}")
    print(f"  Batch Mode — {file_path}")
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

    # Run pipeline for each question
    all_results = []
    for i, q_item in enumerate(questions, 1):
        question = q_item["question"]
        print(f"\n{'─'*60}")
        print(f"[{i}/{len(questions)}] Processing...")
        print(f"{'─'*60}")

        result = run_pipeline(question)
        all_results.append(result)
        print_result(result)

    # Summary
    total = len(all_results)
    passed = sum(1 for r in all_results if r.get("validator") == "PASS")
    failed = sum(1 for r in all_results if r.get("error"))
    print(f"\n{'='*60}")
    print(f"  SUMMARY: {total} questions | {passed} PASS | {failed} errors")
    print(f"{'='*60}")

    # Save batch results to JSON
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
    os.makedirs(output_dir, exist_ok=True)

    from datetime import datetime
    batch_file = os.path.join(output_dir, f"{datetime.now().strftime('%Y-%m-%d')}_batch_results.json")

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
        })

    with open(batch_file, "w", encoding="utf-8") as f:
        json.dump(batch_output, f, ensure_ascii=False, indent=2)

    print(f"\nBatch results saved to: {batch_file}")


def run_interactive():
    """Chế độ hỏi đáp tương tác."""
    from pipeline.pipeline_runner import run_pipeline

    print(f"\n{'='*60}")
    print("  Banking Text2SQL Pipeline — Interactive Mode")
    print(f"{'='*60}")

    while True:
        print()
        question = input("User Question (hoặc 'quit' để thoát): ").strip()

        if not question or question.lower() in ("quit", "exit", "q"):
            print("Tạm biệt!")
            break

        result = run_pipeline(question)
        print_result(result)


def main():
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if not os.path.isabs(file_path):
            file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), file_path)
        run_batch(file_path)
    else:
        run_interactive()


if __name__ == "__main__":
    main()
