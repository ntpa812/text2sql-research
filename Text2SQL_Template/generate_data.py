import time
from pathlib import Path
from rule_engine.profiler import SemanticProfiler
from rule_engine.generator import RuleBasedGenerator

def run_batch_pipeline():
    
    BASE_DIR = Path(__file__).resolve().parent
    INPUT_DIR = BASE_DIR / "data" / "source_tables"      
    PROFILE_DIR = BASE_DIR / "data" / "semantic_profiles" 
    OUTPUT_DIR = BASE_DIR / "output" / "generated_datasets"

    for d in [PROFILE_DIR, OUTPUT_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    if not INPUT_DIR.exists():
        print(f"❌ Lỗi: Không tìm thấy thư mục '{INPUT_DIR}'")
        return

    input_files = list(INPUT_DIR.glob("*.xlsx")) + list(INPUT_DIR.glob("*.csv"))

    profiler = SemanticProfiler()
    generator = RuleBasedGenerator()

    for file_path in input_files:
        table_name = file_path.stem  
        start_time = time.time()
        
        print(f"* Đang xử lý: {file_path.name}...", end=" ", flush=True)

        try:
            profile_json_path = PROFILE_DIR / f"{table_name}.json"
            
            profile_data = profiler.analyze_file(str(file_path), table_name=table_name)
            profiler.save_profile(profile_data, str(profile_json_path))

            dataset = generator.generate_dataset(str(profile_json_path))

            output_excel_path = OUTPUT_DIR / f"ddq_autogen_{table_name}.xlsx"
            generator.export_excel(dataset, str(output_excel_path))

            elapsed = time.time() - start_time
            print(f"Xong! ({len(dataset)} logic) -> Lưu tại: output/{output_excel_path.name}")

        except Exception as e:
            print(f"\n❌ LỖI khi xử lý {table_name}: {e}")

    print("\n" + "="*50)
    print(f"HOÀN TẤT!")
    print(f"\nThư mục kết quả: {OUTPUT_DIR}")
    print("="*50)

if __name__ == "__main__":
    run_batch_pipeline()