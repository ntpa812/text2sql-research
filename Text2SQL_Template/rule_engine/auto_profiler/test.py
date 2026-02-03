import pandas as pd
import json
import os
from auto_profiler import AutoProfiler

# 1. Tạo dữ liệu giả lập (Mock Data)
# Chúng ta cố tình tạo ra các trường hợp để test logic đoán Role:
# - trans_id: Unique -> IDENTITY
# - amount: Số tiền -> METRIC
# - status: Ít giá trị (Success/Fail) -> DIMENSION
# - created_date: Thời gian -> TEMPORAL
data = {
    "trans_id": ["FT001", "FT002", "FT003", "FT004", "FT005"],
    "cust_name": ["Nguyen Van A", "Tran Thi B", "Le Van C", "Pham Van D", "Hoang Thi E"],
    "trans_amount": [500000, 120000, 5000000, 20000, 150000],
    "trans_status": ["SUCCESS", "FAIL", "SUCCESS", "PENDING", "SUCCESS"], # Cardinality thấp
    "created_date": ["2023-10-01", "2023-10-02", "2023-10-03", "2023-10-04", "2023-10-05"],
    "channel_code": ["APP", "WEB", "APP", "ATM", "APP"]
}

# 2. Lưu thành file CSV tạm để test
dummy_path = "dummy_transaction.csv"
df = pd.DataFrame(data)
df.to_csv(dummy_path, index=False)

print(f"[*] Đã tạo file giả lập: {dummy_path}")
print("-" * 50)

# 3. Khởi tạo Profiler
profiler = AutoProfiler()

# --- TEST 1: Kiểm tra logic dịch từ (Unit Test) ---
print("\n[TEST 1] Kiểm tra logic dịch tên cột:")
test_cols = ["cust_id", "trans_amt", "checker_date", "acc_no", "is_active"]
for col in test_cols:
    vn_name = profiler._translate_col_name(col)
    print(f"   {col:<15} -> {vn_name}")

# --- TEST 2: Kiểm tra phân tích toàn bộ file (Integration Test) ---
print("\n[TEST 2] Phân tích file CSV giả lập:")
try:
    profile_result = profiler.analyze(dummy_path)
    
    # In kết quả JSON đẹp đẽ
    print(json.dumps(profile_result, indent=4, ensure_ascii=False))
    
    # Kiểm tra nhanh kết quả mong đợi
    cols = profile_result["columns"]
    print("\n--- ĐÁNH GIÁ KẾT QUẢ ---")
    for col in cols:
        name = col["name"]
        role = col["role"]
        keywords = col["suggested_keywords"]
        print(f"Cột '{name}': Role={role:<10} | Keywords={keywords}")

except Exception as e:
    print(f"❌ Lỗi: {e}")

# 4. Dọn dẹp file tạm
if os.path.exists(dummy_path):
    os.remove(dummy_path)
    print("\n[*] Đã xóa file tạm.")