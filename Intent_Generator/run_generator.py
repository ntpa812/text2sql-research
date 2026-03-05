import os
os.environ["KMP_DUPLICATE_LIB_OK"]="TRUE"
import torch
import time
import json
from pathlib import Path

from rule_engine.profiler import SemanticProfiler
from rule_engine.generator import RuleBasedGenerator
from rule_engine.dict_builder import DictionaryBuilder 

from configs.dictionary import COMMON_DICTIONARY

try:
    from rule_engine.dl_utils import LocalParaphraser
except ImportError:
    LocalParaphraser = None

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

    ai_model = None
    if LocalParaphraser:
        print("Đang khởi động AI Engine...")
        ai_model = LocalParaphraser() 

    profiler = SemanticProfiler()
    dict_builder = DictionaryBuilder()
    
    runtime_dictionary = COMMON_DICTIONARY.copy()
    
    if "specific_columns" not in runtime_dictionary:
        runtime_dictionary["specific_columns"] = {}

    print(f"Dictionary gốc có {len(runtime_dictionary['specific_columns'])} định nghĩa cột thủ công.")
    print("-" * 50)

    for file_path in input_files:
        table_name = file_path.stem.split(' - ')[0] 
        print(f"[*] Xử lý bảng: {table_name}")
        
        try:
            start_time = time.time()

            profile = profiler.analyze_file(str(file_path), table_name)
            profile_json_path = PROFILE_DIR / f"{table_name}.json"
            profiler.save_profile(profile, str(profile_json_path))

            new_specifics = dict_builder.process_file(file_path)
            print(f"Done. (Profile xong)")

            print(f"[*] DictBuilder đang học từ {len(new_specifics)} cột của bảng {table_name}...")
            for col, keywords in new_specifics.items():
                if col in runtime_dictionary["specific_columns"]:
                    existing = set(runtime_dictionary["specific_columns"][col])
                    existing.update(keywords)
                    runtime_dictionary["specific_columns"][col] = list(existing)
                else:
                    runtime_dictionary["specific_columns"][col] = keywords
            
            print(f"Done. (Biết thêm {len(new_specifics)} cột)")

            generator = RuleBasedGenerator(vocab=runtime_dictionary, ai_model=ai_model) 

            dataset = generator.generate_dataset(str(profile_json_path))

            output_excel_path = OUTPUT_DIR / f"ddq_autogen_{table_name}.xlsx"
            generator.export_excel(dataset, str(output_excel_path))

            elapsed = time.time() - start_time
            print(f"Xong bảng {table_name} trong {elapsed:.2f}s ({len(dataset)} intents)")

        except Exception as e:
            print(f"\n❌ LỖI khi xử lý {table_name}: {e}")
            import traceback
            traceback.print_exc()

        print("-" * 30)

    with open(BASE_DIR / "configs" / "learned_dictionary_dump.json", "w", encoding="utf-8") as f:
        json.dump(runtime_dictionary, f, ensure_ascii=False, indent=4)
    
    print("\n" + "="*50)
    print(f"HOÀN TẤT! Đã lưu dictionary học được tại configs/learned_dictionary_dump.json")
    print(f"Thư mục kết quả: {OUTPUT_DIR}")

if __name__ == "__main__":
    run_batch_pipeline()