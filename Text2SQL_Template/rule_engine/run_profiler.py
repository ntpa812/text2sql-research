from rule_engine.profiler import SemanticProfiler
import os
from pathlib import Path

if __name__ == "__main__":

    BASE_DIR = Path(__file__).resolve().parent
    
    INPUT_DIR = BASE_DIR / "data"
    OUTPUT_DIR = BASE_DIR / "profiles"
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    FILE_NAME = "transaction.xlsx"
    input_path = INPUT_DIR / FILE_NAME

    if not input_path.exists():
        print(f"❌ Lỗi: Không tìm thấy file tại {input_path}")
    else:
        file_stem = input_path.stem
        output_path = OUTPUT_DIR / f"semantic_profile_{file_stem}.json"
        
        profiler = SemanticProfiler()
        
        try:
            print(f"[*] Đang phân tích file: {input_path}")

            profile_data = profiler.analyze_file(str(input_path), table_name=file_stem)
            
            profiler.save_profile(profile_data, str(output_path))
            print(f"Thành công! File lưu tại: {output_path}")
            
        except Exception as e:
            print(f"❌ Lỗi: {e}")