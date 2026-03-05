import pandas as pd
import re
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any

sys.path.append(str(Path(__file__).resolve().parent.parent))

from configs.dictionary import COMMON_DICTIONARY

from sentence_transformers import SentenceTransformer, util
import torch

class SemanticProfiler:
    def __init__(self):
        self.vocab = COMMON_DICTIONARY
        self.glossary = {}
        self._build_glossary()
        
        self.model = None
        try:
            self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        except:
            print("Warning: Could not load SentenceTransformer model. AI guessing will be disabled.")

        self.concepts = [
            "số tiền", "mã giao dịch", "ngày giao dịch", "trạng thái",
            "số tài khoản", "khách hàng", "kênh", "nội dung",
            "phí", "người thụ hưởng", "ngân hàng", "lãi suất",
            "chi nhánh", "sản phẩm", "tiền tệ"
        ]
        
        if self.model:
            self.concept_embeddings = self.model.encode(self.concepts, convert_to_tensor=True)
        else:
            self.concept_embeddings = None

        self.rules = {
            "IDENTITY": {
                "col_pattern": r"(_id|_code|_no|_key|_number|id|user_name)$",
                "desc_pattern": r"(mã|khóa|định danh|số thẻ|số tài khoản|duy nhất|user_name)",
                "sql_op": "WHERE {col} = '{val}'"
            },
            "TEMPORAL": {
                "col_pattern": r"(_time|_date|_at|_on|dob)$",
                "desc_pattern": r"(thời gian|ngày|giờ|thời điểm|năm|tháng)",
                "sql_op": "WHERE {col} BETWEEN '{start}' AND '{end}'"
            },
            "DIMENSION": {
                "col_pattern": r"(_type|_status|_channel|_mode|_currency|_state|_method|_name|_fullname|source_type)$",
                "desc_pattern": r"(loại|trạng thái|kênh|tiền tệ|phương thức|nguồn|tên|người nhận|người gửi)",
                "sql_op": "WHERE {col} = '{val}'"
            },
            "METRIC": {
                "col_pattern": r"(_amount|_fee|_val|_balance|_cost|_price|_tax|_limit)$",
                "desc_pattern": r"(số tiền|giá trị|phí|thuế|hạn mức|dư nợ|chiết khấu)",
                "sql_op": "SUM({col})"
            }
        }

    def _build_glossary(self):
        for k, v in self.vocab.get("col_mapping", {}).items():
            self.glossary[k] = v[0]
        for k, v in self.vocab.get("tables", {}).items():
            self.glossary[k] = v[0]
        for k, v in self.vocab.get("suffixes", {}).items():
            clean_k = k.replace("_", "")
            self.glossary[clean_k] = v[0]
            
        extras = {
            "amt": "số tiền", "val": "giá trị", "bal": "số dư",
            "dt": "ngày", "tm": "giờ", "cd": "mã",
            "no": "số", "id": "mã", "desc": "nội dung",
            "cif": "khách hàng", "cust": "khách hàng",
            "trans": "giao dịch"
        }
        self.glossary.update(extras)

    def _extract_primary_definition(self, desc: str) -> str:
        """
        Extracts the main definition from the beginning of the description string.
        Splits by separators like (, -, :, etc.
        """
        if not desc: return ""
        
        clean_desc = desc.strip()
        
        separators = r"[\(\:\-\,\.]"
        parts = re.split(separators, clean_desc)
        
        primary = parts[0].strip()
        
        stopwords_prefix = [
            "là trường", "là cột", "trường này là", "cột này là", 
            "dùng để", "lưu trữ", "biểu thị", "chứa thông tin", "thông tin về"
        ]
        
        lower_primary = primary.lower()
        for prefix in stopwords_prefix:
            if lower_primary.startswith(prefix):
                primary = primary[len(prefix):].strip()
                break
                
        return primary.lower()
    
    def _ai_guess(self, text: str) -> str:
        if not self.model or self.concept_embeddings is None: return text
        embedding = self.model.encode(text, convert_to_tensor=True)
        scores = util.cos_sim(embedding, self.concept_embeddings)[0]
        best_idx = torch.argmax(scores).item()
        if scores[best_idx].item() > 0.45:
            return self.concepts[best_idx]
        return text

    def _translate_col_name(self, col_name: str) -> str:
        parts = col_name.lower().split('_')
        translated_parts = []
        for p in parts:
            if p in self.glossary:
                translated_parts.append(self.glossary[p])
            else:
                guessed = self._ai_guess(p)
                translated_parts.append(guessed)

        raw_vn = " ".join(translated_parts)
        words = raw_vn.split()
        if len(words) > 1:
            prefixes = ["mã", "tên", "ngày", "số", "loại", "trạng thái"]
            if words[-1] in prefixes:
                last = words.pop()
                words.insert(0, last)
        return " ".join(words)

    def _clean_keywords(self, text: str) -> List[str]:
        if not isinstance(text, str): return []
        text = text.lower()
        keywords = []

        matches = re.findall(r"\((.*?)\)", text)
        for m in matches:
            clean_m = re.sub(r'(?i)^(ví dụ|vd|ex|eg|như)\s*[:\.\-]?\s*', '', m.strip())
            if ',' in clean_m:
                parts = [p.strip() for p in clean_m.split(',') if p.strip()]
                keywords.extend(parts)
            else:
                if clean_m: keywords.append(clean_m)

        main_text_raw = re.sub(r"\(.*?\)", "", text).strip()
        raw_phrases = re.split(r'[/,;\.\-]', main_text_raw)

        db_jargon = [
            "primary key", "khóa chính", "foreign key", "khóa ngoại",
            "not null", "nullable", "unique", "constraint", "ràng buộc",
            "auto increment", "tự tăng", "index", "chỉ mục",
            "tham chiếu đến", "quan hệ với", "bảng", "table", "column", "bản ghi"
        ]

        stopwords = [
            "là", "của", "người", "dùng", "hệ thống", "ví dụ", "trong", "để", 
            "trường", "cột", "thông tin", "dữ liệu", "chứa", "lưu", "được", "tại", 
            "id", "hợp", "này", "các", "những", "cái", "hoặc", "nếu", "khi", "thì"
        ]

        for phrase in raw_phrases:
            phrase = phrase.strip()
            if not phrase: continue

            for term in db_jargon:
                phrase = phrase.replace(term, " ")
            
            for w in stopwords:
                phrase = phrase.replace(f" {w} ", " ")
                if phrase.startswith(f"{w} "): phrase = phrase[len(w)+1:]
                if phrase.endswith(f" {w}"): phrase = phrase[:-len(w)-1]

            phrase = re.sub(r'[0-9|.,\-_:]+', ' ', phrase)
            clean_phrase = " ".join(phrase.split())

            word_count = len(clean_phrase.split())
            if 1 < len(clean_phrase) and word_count <= 5:
                keywords.append(clean_phrase)

        seen = set()
        deduped = []
        for k in keywords:
            k = k.strip()
            if k and k not in seen:
                seen.add(k)
                deduped.append(k)
                
        return deduped[:6]

    def _detect_role(self, col_name: str, description: str) -> str:
        col_name = col_name.lower()
        description = str(description).lower()
        for role, rule in self.rules.items():
            if re.search(rule["col_pattern"], col_name):
                return role
            if re.search(rule["desc_pattern"], description):
                return role
        return "ATTRIBUTE"
    
    def _detect_value_group(self, col_name: str) -> str:
        mapping = self.vocab.get("category_mapping", {})
        col_lower = col_name.lower()
        
        for keyword, group_code in mapping.items():
            if keyword in col_lower:
                return group_code
            
        if "currency" in col_lower or "ccy" in col_lower:
            return "CURRENCY"    
            
        return None

    def analyze_file(self, file_path: str, table_name: str = "auto_detect") -> Dict[str, Any]:
        
        path_obj = Path(file_path)
        
        df = pd.read_excel(path_obj) if path_obj.suffix == '.xlsx' else pd.read_csv(path_obj)

        table_name = path_obj.stem.lower().split(" - ")[0]
        
        profile = {
            "table_name": table_name, 
            "version": "1.0",
            "columns": []
        }
        
        df.columns = [c.strip().lower() for c in df.columns]
        
        col_name_key = next((c for c in df.columns if any(x in c for x in ["tên", "name", "field", "cột"])), None)
        desc_key = next((c for c in df.columns if any(x in c for x in ["mô tả", "desc", "content"])), None)

        if not col_name_key:
            raise ValueError(f"Không tìm thấy cột Header trong {file_path}")

        if table_name == "auto_detect":
            table_name = os.path.splitext(os.path.basename(file_path))[0].split(" - ")[0]

        profile = {"table_name": table_name, "columns": []}

        for _, row in df.iterrows():
            col_raw = str(row[col_name_key]).strip()
            desc_raw = str(row[desc_key]).strip() if desc_key else ""
            
            if not col_raw or col_raw.lower() == "nan":
                continue

            role = self._detect_role(col_raw, desc_raw)
            
            
            keyword_list = []
            
            primary_def = self._extract_primary_definition(desc_raw)
            if primary_def:
                keyword_list.append(primary_def)
                
            translated_name = self._translate_col_name(col_raw)
            if translated_name:
                keyword_list.append(translated_name)
                
            desc_keywords = self._clean_keywords(desc_raw)
            keyword_list.extend(desc_keywords)
            
            if role == "IDENTITY" and "mã" in translated_name:
                keyword_list.append(translated_name.replace("mã", "số"))
            
            final_keywords = list(dict.fromkeys([k for k in keyword_list if k]))
            
            if not final_keywords:
                final_keywords = [translated_name if translated_name else col_raw]
            
            value_ref = None
            if role in ["DIMENSION", "ATTRIBUTE"]:
                value_ref = self._detect_value_group(col_raw)
                if value_ref and role == "ATTRIBUTE":
                    role = "DIMENSION"
            
            profile["columns"].append({
                "name": col_raw,
                "role": role,
                "description": desc_raw,
                "suggested_keywords": final_keywords, 
                "sql_logic": self.rules.get(role, {}).get("sql_op", ""),
                "value_ref": value_ref
            })

        return profile

    def save_profile(self, profile: Dict, output_path: str):
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=4)
            
            
# if __name__ == "__main__":
#     current_file_path = Path(__file__).resolve()
#     project_root = current_file_path.parent.parent  
    
#     input_path = project_root / "data" / "source_tables" / "customer.xlsx"
    
#     output_path = project_root / "data" / "semantic_profiles" / "customer.json"

#     profiler = SemanticProfiler()
#     profile = profiler.analyze_file(str(input_path))
            
#     profiler.save_profile(profile, str(output_path))
#     print(f"Thành công! Profile đã được lưu tại: {output_path}")