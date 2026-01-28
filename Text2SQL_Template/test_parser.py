import sys
from pathlib import Path
from sql_parser.core import RuleBasedParser
from sql_parser.batch_worker import process_excel_file

BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = BASE_DIR / "data" / "semantic_profiles"
INPUT_DIR = BASE_DIR / "data" / "parser_inputs"      
OUTPUT_DIR = BASE_DIR / "output" / "parser_outputs"

for d in [INPUT_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def list_profiles():
    return list(PROFILE_DIR.glob("*.json"))

def mode_test_single():
    profiles = list_profiles()
    if not profiles:
        print("❌ Không tìm thấy Profile nào trong thư mục 'semantic_profiles'. Hãy chạy rule_engine trước!")
        return

    # Mặc định lấy profile đầu tiên (ví dụ transaction.json)
    selected_profile = profiles[0]
    print(f"🔧 Đang sử dụng Profile: {selected_profile.name}")
    
    parser = RuleBasedParser(str(selected_profile))
    
    print("\n--- CHẾ ĐỘ TEST NHANH (Gõ 'exit' để thoát) ---")
    while True:
        q = input("\n[NLQ] Nhập câu hỏi: ")
        if q.lower() in ["exit", "quit"]: break
        
        res = parser.parse(q)
        if "error" in res:
            print(f"❌ Lỗi: {res['error']}")
        else:
            print(f"✅ SQL: \033[92m{res['sql']}\033[0m") 
            print(f"   Giải thích: {res['explanation']}")

def mode_batch_excel():
    # Input
    input_files = list(INPUT_DIR.glob("*.xlsx"))
    if not input_files:
        print(f"❌ Thư mục '{INPUT_DIR}' trống! Hãy copy file Excel chứa câu hỏi vào đó.")
        return

    print("\nDanh sách file Input:")
    for i, f in enumerate(input_files):
        print(f"{i+1}. {f.name}")
    
    choice = int(input("👉 Chọn số thứ tự file muốn chạy: ")) - 1
    selected_input = input_files[choice]

    # Chọn Profile (Table context)
    profiles = list_profiles()
    print("\nChọn ngữ cảnh bảng (Profile):")
    for i, f in enumerate(profiles):
        print(f"{i+1}. {f.name}")
    
    p_choice = int(input("👉 Chọn số thứ tự Profile: ")) - 1
    selected_profile = profiles[p_choice]

    output_file = OUTPUT_DIR / f"parsed_result_{selected_input.name}"
    process_excel_file(selected_input, output_file, selected_profile)

if __name__ == "__main__":
    print("=== TOOL KIỂM THỬ PARSER (NLQ -> SQL) ===")
    print("1. Test nhanh từng câu (Interactive)")
    print("2. Chạy Batch file Excel (Bulk Process)")
    
    opt = input("👉 Chọn chế độ (1/2): ")
    
    if opt == "1":
        mode_test_single()
    elif opt == "2":
        mode_batch_excel()
    else:
        print("Lựa chọn không hợp lệ.")