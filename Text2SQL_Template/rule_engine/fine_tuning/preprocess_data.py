import pandas as pd
import json
import re
import os

def clean_text(text):
    if not isinstance(text, str): return ""
    return text.strip().replace('\n', ' ')

def convert_to_training_data(file_path, output_path):
    if file_path.endswith('.csv'):
        df = pd.read_csv(file_path)
    else:
        df = pd.read_excel(file_path)

    training_pairs = []

    print(f"[*] Đang xử lý file: {file_path}")
    
    for _, row in df.iterrows():
        description = clean_text(row.get('description', ''))
        
        examples_raw = row.get('examples', '')
        if not description or not isinstance(examples_raw, str):
            continue
            
        example_list = re.split(r'[,\n]+', examples_raw)
        
        for ex in example_list:
            ex = clean_text(ex)
            if len(ex) > 5: 
                entry = {
                    "input": f"paraphrase: {ex}",
                    "target": description
                }
                training_pairs.append(entry)

    with open(output_path, 'w', encoding='utf-8') as f:
        for entry in training_pairs:
            json.dump(entry, f, ensure_ascii=False)
            f.write('\n')
            
    print(f"Đã tạo thành công {len(training_pairs)} cặp dữ liệu training!")
    print(f"💾 File lưu tại: {output_path}")

if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    possible_files = [
        "ddq_getTransactionHistory_v2.xlsx"
    ]
    
    output_name = "train_data.jsonl"
    output_path = os.path.join(current_dir, output_name)
    
    final_input_path = None
    
    for fname in possible_files:
        fpath = os.path.join(current_dir, fname)
        if os.path.exists(fpath):
            final_input_path = fpath
            break
            
    if not final_input_path:
        print(f"❌ LỖI: Không tìm thấy file input tại: {current_dir}")
        exit()

    convert_to_training_data(final_input_path, output_path)