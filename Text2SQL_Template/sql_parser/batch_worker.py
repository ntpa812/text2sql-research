import pandas as pd
from pathlib import Path
from .core import RuleBasedParser

def process_excel_file(input_path: Path, output_path: Path, profile_path: Path):
    print(f"[*] Đang khởi tạo Parser với profile: {profile_path.name}")
    parser = RuleBasedParser(str(profile_path))
    
    print(f"[*] Đang đọc file câu hỏi: {input_path.name}")
    try:
        df = pd.read_excel(input_path)
    except Exception as e:
        print(f"❌ Lỗi đọc file Excel: {e}")
        return

    # Giả định cột chứa câu hỏi tên là "question" hoặc cột đầu tiên
    question_col = "question"
    if "question" not in df.columns:
        question_col = df.columns[0] 
        print(f"⚠️ Không thấy cột 'question', đang dùng cột: '{question_col}'")

    results = []
    print("[*] Đang dịch NLQ sang SQL...")
    
    for idx, row in df.iterrows():
        q = str(row[question_col])
        res = parser.parse(q)
        
        row_data = row.to_dict()
        if "error" in res:
            row_data["generated_sql"] = "ERROR"
            row_data["parser_note"] = res["error"]
        else:
            row_data["generated_sql"] = res["sql"]
            row_data["parser_intent"] = res["intent"]
            row_data["parser_entities"] = res["entities"]
            row_data["parser_explanation"] = res["explanation"]
            
        results.append(row_data)

    output_df = pd.DataFrame(results)
    output_df.to_excel(output_path, index=False)
    print(f"✅ Hoàn tất! Kết quả lưu tại: {output_path}")