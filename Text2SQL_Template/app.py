"""
Banking Text2SQL – Entry Point
Chạy pipeline cho câu hỏi tiếng Việt → SQL → kết quả.
"""

import sys
import os
import logging

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    from pipeline.pipeline_runner import run_pipeline

    print("\n" + "=" * 60)
    print("  Banking Text2SQL Pipeline")
    print("=" * 60)

    while True:
        print()
        question = input("User Question (hoặc 'quit' để thoát): ").strip()

        if not question or question.lower() in ("quit", "exit", "q"):
            print("Tạm biệt!")
            break

        print(f"\nĐang xử lý: {question}")
        print("-" * 40)

        result = run_pipeline(question)

        # Hiển thị kết quả
        print(f"\n{'='*40} KẾT QUẢ {'='*40}")

        if result.get("error"):
            print(f"Lỗi: {result['error']}")
        else:
            # Intent đã chọn
            print(f"\n--- Intent đã chọn ---")
            print(f"  ID:          {result.get('intent', 'N/A')}")
            print(f"  Tên:         {result.get('intent_name', 'N/A')}")
            print(f"  Mô tả:       {result.get('intent_description', 'N/A')}")
            if result.get('intent_sql_template'):
                print(f"  SQL Template: {result['intent_sql_template'][:120]}...")

            # Entities & SQL
            print(f"\n--- Entities ---")
            for k, v in result.get('entities', {}).items():
                print(f"  {k}: {v}")

            print(f"\n--- SQL đã sinh ---")
            print(f"  {result.get('sql_generated', 'N/A')}")
            print(f"  Validator: {result.get('validator_status', 'N/A')} | Retry: {result.get('retry_count', 0)}")

            # Kết quả DB
            print(f"\n--- Kết quả từ DB ({result.get('result_count', 0)} rows) ---")
            rows = result.get('result_data', [])
            if rows:
                # Header
                cols = list(rows[0].keys())
                print(f"  {' | '.join(cols)}")
                print(f"  {'-+-'.join('-' * min(len(c), 20) for c in cols)}")
                for row in rows[:10]:
                    vals = [str(row.get(c, ''))[:20] for c in cols]
                    print(f"  {' | '.join(vals)}")
                if len(rows) > 10:
                    print(f"  ... và {len(rows) - 10} dòng nữa")
            else:
                print("  Không có kết quả.")

            # Giải thích
            if result.get("explain"):
                print(f"\n--- Giải thích ---")
                print(f"  {result['explain']}")

            print(f"\nThời gian: {result.get('execution_time', 0):.2f}s")

        print("=" * 89)


if __name__ == "__main__":
    main()
