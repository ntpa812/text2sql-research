import sys
import os
from pathlib import Path

# Thêm đường dẫn gốc vào sys.path để import được các module
sys.path.append(str(Path(__file__).resolve().parent))

from sql_parser.core import SchemaRouter

# --- CẤU HÌNH ---
# Đảm bảo đường dẫn này trỏ đúng đến nơi bạn lưu các file .json (sau khi chạy profiler)
PROFILE_DIR = "./data/semantic_profiles" 

def run_test():
    # 1. Kiểm tra thư mục profile
    if not os.path.exists(PROFILE_DIR):
        print(f"❌ Lỗi: Không tìm thấy thư mục '{PROFILE_DIR}'.")
        print("👉 Bạn cần chạy 'python rule_engine/profiler.py' để tạo file JSON trước.")
        return

    print("⏳ Đang khởi tạo Router và Vector Database (lần đầu sẽ hơi lâu để tải model)...")
    try:
        router = SchemaRouter(PROFILE_DIR)
        print("✅ Khởi tạo thành công!\n")
    except Exception as e:
        print(f"❌ Lỗi khởi tạo: {e}")
        return

    # 2. Danh sách câu hỏi test (Đa dạng để kiểm tra độ thông minh)
    test_queries = [
        # Test bảng Transaction (Giao dịch)
        "Liệt kê các giao dịch chuyển tiền hôm qua",
        "Tìm mã giao dịch ABC truyen tien", 
        
        # Test bảng Customer Account (Tài khoản/Số dư)
        "Số dư hiện tại của tôi là bao nhiêu?",
        "Kiểm tra tài khoản tiết kiệm",
        
        # Test bảng Customer (Thông tin khách hàng)
        "Thông tin khách hàng có mã CIF 123456",
        "Địa chỉ của khách hàng Nguyễn Văn A"
    ]

    print("--- BẮT ĐẦU TEST LOGIC ---")
    for q in test_queries:
        print(f"\n❓ Câu hỏi: '{q}'")
        
        # Gọi hàm parse
        result = router.parse(q)
        
        # In kết quả
        table = result.get("detected_table", "N/A")
        sql = result.get("sql", "")
        error = result.get("error", None)
        
        if error:
            print(f"   ⚠️  AI chọn bảng: {table}")
            print(f"   ❌ Lỗi logic: {error}")
        else:
            print(f"   🎯 AI chọn bảng: {table.upper()}") # Quan trọng: Xem nó chọn đúng bảng không
            print(f"   💻 SQL sinh ra: {sql}")

if __name__ == "__main__":
    run_test()