import pandas as pd
from pathlib import Path
from .core import SchemaRouter 

def process_excel_file(input_path: Path, output_path: Path, profile_dir: Path):
    print(f"[*] Đang khởi tạo Router với thư mục profile: {profile_dir}")
    router = SchemaRouter(profile_dir)
    
    print(f"[*] Đang đọc file câu hỏi: {input_path.name}")
    df = pd.read_excel(input_path)
    
    question_col = "question"
    if "question" not in df.columns:
        if len(df.columns) > 0:
            question_col = df.columns[0]
            print(f"⚠️ Không thấy cột 'question', đang dùng cột: '{question_col}'")
        else:
            print("❌ File Excel rỗng!")
            return

    results = []
    print("[*] Đang dịch NLQ sang SQL...")
    
    for idx, row in df.iterrows():
        q = str(row[question_col])
        
        res = router.parse(q)
        
        row_data = row.to_dict()
        
        if res.get("error"):
            row_data["generated_sql"] = "ERROR"
            row_data["parser_note"] = res.get("error")
            row_data["parser_intent"] = res.get("intent", "UNKNOWN")
            row_data["detected_table"] = res.get("detected_table", "N/A")
        else:
            row_data["generated_sql"] = res.get("sql")
            row_data["parser_note"] = res.get("explanation")
            row_data["parser_intent"] = res.get("intent", "LOOKUP")
            row_data["detected_table"] = res.get("detected_table", "Unknown")
            
        results.append(row_data)
        
    try:
        result_df = pd.DataFrame(results)
        result_df.to_excel(output_path, index=False)
        print(f"Đã xuất kết quả ra: {output_path}")
    except Exception as e:
        print(f"❌ Lỗi khi ghi file output: {e}")