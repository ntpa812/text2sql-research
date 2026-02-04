import sys
from pathlib import Path
from sql_parser.core import SchemaRouter
from sql_parser.batch_worker import process_excel_file
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
PROFILE_DIR = BASE_DIR / "data" / "semantic_profiles"
INPUT_DIR = BASE_DIR / "data" / "parser_inputs"      
OUTPUT_DIR = BASE_DIR / "output" / "parser_outputs"

for d in [INPUT_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

def list_profiles():
    return list(PROFILE_DIR.glob("*.json"))

def mode_batch_excel():

    input_files = list(INPUT_DIR.glob("*.xlsx"))
    
    for i, input_path in enumerate(input_files):

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        output_file = OUTPUT_DIR / f"parsed_result_{input_path.stem}_{timestamp}.xlsx"
        print(f"--- [{i+1}/{len(input_files)}] Đang xử lý file: {input_path.name} ---")
        
        process_excel_file(input_path, output_file, PROFILE_DIR)

if __name__ == "__main__":

    mode_batch_excel()
