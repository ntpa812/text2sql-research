# coding: utf-8
"""
Script xử lý các file Excel trong outputs/:
1. Đọc tất cả file Excel
2. Lấy 2 cột: input_query và expected_Documents
3. Loại bỏ trùng lặp theo cặp (input_query, expected_Documents)
4. Đổi tên thành query và Documents
5. Sắp xếp theo Documents, rồi theo query
6. Lưu vào outputs_processed/
"""

import pandas as pd
from pathlib import Path
from datetime import datetime


def process_outputs():
    """Xử lý tất cả file Excel trong outputs/"""

    outputs_dir = Path("outputs")
    processed_dir = Path("outputs_processed")

    # Tạo thư mục output nếu chưa có
    processed_dir.mkdir(exist_ok=True)

    # Tìm tất cả file Excel
    excel_files = list(outputs_dir.glob("*.xlsx")) + list(outputs_dir.glob("*.xls"))

    if not excel_files:
        print("❌ Không tìm thấy file Excel nào trong outputs/")
        return

    print(f"📂 Tìm thấy {len(excel_files)} file Excel trong outputs/")

    # Đọc và gộp tất cả file
    all_data = []
    files_processed = 0
    rows_total = 0

    for file_path in excel_files:
        try:
            df = pd.read_excel(file_path)

            # Kiểm tra có cột cần thiết không
            if 'input_query' not in df.columns or 'expected_Documents' not in df.columns:
                print(f"  ⚠️  {file_path.name}: Thiếu cột input_query hoặc expected_Documents, bỏ qua")
                continue

            # Lấy 2 cột cần thiết
            subset = df[['input_query', 'expected_Documents']].copy()

            # Loại bỏ các dòng có giá trị rỗng
            subset = subset.dropna(subset=['input_query'])
            subset = subset[subset['input_query'].astype(str).str.strip() != '']

            rows_before = len(subset)
            all_data.append(subset)
            rows_total += rows_before
            files_processed += 1

            print(f"  ✅ {file_path.name}: {rows_before} dòng")

        except Exception as e:
            print(f"  ❌ {file_path.name}: Lỗi - {e}")

    if not all_data:
        print("❌ Không có dữ liệu hợp lệ để xử lý")
        return

    # Gộp tất cả
    merged_df = pd.concat(all_data, ignore_index=True)
    print(f"\n📊 Tổng cộng: {rows_total} dòng từ {files_processed} file")

    # Loại bỏ trùng lặp theo cặp (input_query, expected_Documents)
    before_dedup = len(merged_df)
    merged_df = merged_df.drop_duplicates(subset=['input_query', 'expected_Documents'])
    after_dedup = len(merged_df)

    print(f"🔄 Loại bỏ trùng lặp: {before_dedup} → {after_dedup} dòng (giảm {before_dedup - after_dedup})")

    # Đổi tên cột
    merged_df = merged_df.rename(columns={
        'input_query': 'query',
        'expected_Documents': 'Documents'
    })

    # Sắp xếp theo Documents, rồi theo query
    merged_df = merged_df.sort_values(by=['Documents', 'query'], na_position='last')
    merged_df = merged_df.reset_index(drop=True)

    # Tạo tên file output
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"merged_queries_{timestamp}.xlsx"
    output_path = processed_dir / output_filename

    # Lưu file
    merged_df.to_excel(output_path, index=False, sheet_name='Queries')

    print(f"\n✅ Đã lưu: {output_path}")
    print(f"   - Tổng số dòng: {len(merged_df)}")
    print(f"   - Số Documents khác nhau: {merged_df['Documents'].nunique()}")

    # Thống kê theo Documents
    print("\n📈 Thống kê theo Documents:")
    documents_counts = merged_df['Documents'].value_counts()
    for documents, count in documents_counts.head(10).items():
        print(f"   {documents}: {count} queries")
    if len(documents_counts) > 10:
        print(f"   ... và {len(documents_counts) - 10} Documents khác")

    return output_path


if __name__ == "__main__":
    print("=" * 60)
    print("PROCESS OUTPUTS - Gộp và loại bỏ trùng lặp")
    print("=" * 60)
    print()

    process_outputs()

    print()
    print("=" * 60)
    print("DONE!")
    print("=" * 60)
