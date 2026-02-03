import pandas as pd
import re
import sys
import json
from pathlib import Path
from typing import List, Dict, Any, Set

project_root = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(project_root))

try:
    from configs.dictionary import COMMON_DICTIONARY
except ImportError:
    COMMON_DICTIONARY = {}

class DictionaryBuilder:
    def __init__(self):
        self.base_vocab = COMMON_DICTIONARY
        self.glossary = {}
        self._build_glossary()

    def _build_glossary(self):
        """Xây dựng glossary từ config hiện tại"""
        for k, v in self.base_vocab.get("col_mapping", {}).items():
            self.glossary[k] = v[0]
        for k, v in self.base_vocab.get("suffixes", {}).items():
            clean_k = k.replace("_", "")
            self.glossary[clean_k] = v[0]
        
        self.glossary.update({
            "id": "mã", "code": "mã", "date": "ngày", 
            "time": "thời gian", "no": "số", "amt": "số tiền",
            "desc": "mô tả", "content": "nội dung"
        })

    def _clean_description(self, desc: str) -> List[str]:
        if not isinstance(desc, str): return []
        stopwords = [
            "là trường", "là cột", "dùng để", "lưu trữ", "thông tin", "của", "tại", 
            "hệ thống", "tương ứng", "được", "bảng", "dữ liệu", "nullable", "primary key",
            "mô tả", "cho", "chi tiết", "về"
        ]
        text = desc.lower()
        text = re.sub(r'\(.*?\)', '', text) 
        text = re.sub(r'[0-9|.,\-_:]+', ' ', text)
        for word in stopwords:
            text = text.replace(word, " ")
        clean_text = " ".join(text.split())
        return [clean_text] if clean_text else []

    def _translate_col_name(self, col_name: str) -> str:
        parts = col_name.lower().split('_')
        translated = []
        for p in parts:
            translated.append(self.glossary.get(p, p))
        if len(translated) > 1:
            if translated[-1] in ["mã", "tên", "ngày", "số", "loại", "trạng thái"]:
                last = translated.pop()
                translated.insert(0, last)
        return " ".join(translated)

    def process_file(self, file_path: Path) -> Dict[str, List[str]]:
        try:
            df = pd.read_excel(file_path)
            df.columns = [c.strip() for c in df.columns]
        except Exception as e:
            print(f"❌ Lỗi đọc file {file_path.name}: {e}")
            return {}

        possible_headers = ["Field", "Column Name", "Tên Cột", "Name"]
        possible_descs = ["Description", "Mô tả", "Desc", "Content"]
        
        col_header = next((h for h in possible_headers if h in df.columns), None)
        desc_header = next((h for h in possible_descs if h in df.columns), None)

        if not col_header: return {}

        local_dict = {}
        for _, row in df.iterrows():
            col_raw = str(row[col_header]).strip()
            desc_raw = row.get(desc_header, "")
            col_key = col_raw.lower()
            
            synonyms = set()
            synonyms.add(self._translate_col_name(col_raw))
            synonyms.update(self._clean_description(desc_raw))
            
            if "mã" in synonyms: # Logic ID
                synonyms.add(self._translate_col_name(col_raw).replace("mã", "số"))

            local_dict[col_key] = list(synonyms)
        return local_dict

    def save_as_python_file(self, data: Dict, output_path: Path):
        """
        Lưu dictionary dưới dạng file Python (.py)
        để giống hệt format của dictionary.py gốc
        """
        json_str = json.dumps(data, indent=4, ensure_ascii=False)
        
        py_str = json_str.replace("null", "None").replace("false", "False").replace("true", "True")
        
        try:
            print(f"✅ Đã lưu file Python tại: {output_path}")
        except Exception as e:
            print(f"❌ Lỗi lưu file: {e}")

    def build_from_profile_data(self, profile_data: Dict) -> Dict[str, List[str]]:
        specific_columns = {}
        
        columns = profile_data.get("columns", [])
        print(f"[*] DictBuilder đang học từ {len(columns)} cột của bảng {profile_data.get('table_name')}...")

        for col_info in columns:
            col_raw = str(col_info.get("name", "")).strip()
            desc_raw = str(col_info.get("description", "")) 
            
            col_key = col_raw.lower()
            synonyms = set()

            translated = self._translate_col_name(col_raw)
            synonyms.add(translated)

            if desc_raw and desc_raw.lower() != "nan":
                desc_keywords = self._clean_description(desc_raw)
                synonyms.update(desc_keywords)

            if "mã" in translated:
                synonyms.add(translated.replace("mã", "số"))

            if "suggested_keywords" in col_info:
                synonyms.update(col_info["suggested_keywords"])

            specific_columns[col_key] = list(synonyms)

        return specific_columns
    
    def build_full_dictionary(self, source_dir: Path, output_path: Path):

        ordered_keys = [
            "tables", "suffixes", "specific_columns", "values", 
            "time_phrases", "verbs", "nouns", "connectors", 
            "col_mapping", "abbreviations"
        ]
        
        final_dict = {}
        master_specifics = self.base_vocab.get("specific_columns", {}).copy()

        files = list(source_dir.glob("*.xlsx")) + list(source_dir.glob("*.xls"))
        
        for file_path in files:
            file_dict = self.process_file(file_path)
            for col, syns in file_dict.items():
                if col in master_specifics:
                    existing = set(master_specifics[col])
                    existing.update(syns)
                    master_specifics[col] = list(existing)
                else:
                    master_specifics[col] = syns

        for key in ordered_keys:
            if key == "specific_columns":
                final_dict[key] = master_specifics
            else:
                final_dict[key] = self.base_vocab.get(key, {})

        self.save_as_python_file(final_dict, output_path)

if __name__ == "__main__":
    builder = DictionaryBuilder()
    source_directory = project_root / "data" / "source_tables"
    
    output_file = project_root / "configs" / "dictionary_updated.py"

    builder.build_full_dictionary(source_directory, output_file)