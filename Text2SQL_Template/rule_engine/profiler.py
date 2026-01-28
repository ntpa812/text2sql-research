import pandas as pd
import re
import json
import os
from typing import Dict, List, Any
class SemanticProfiler:
    def __init__(self):

        self.rules = {
            "IDENTITY": {
                "col_pattern": r"(_id|_code|_no|_key|_number|id)$",
                "desc_pattern": r"(mã|khóa|định danh|số thẻ|số tài khoản|duy nhất|user_name)",
                "sql_op": "WHERE {col} = '{val}'"
            },
            "TEMPORAL": {
                "col_pattern": r"(_time|_date|_at|_on|dob)$",
                "desc_pattern": r"(thời gian|ngày|giờ|thời điểm|năm|tháng)",
                "sql_op": "WHERE {col} BETWEEN '{start}' AND '{end}'"
            },
            "METRIC": {
                "col_pattern": r"(_amount|_fee|_val|_balance|_cost|_price|_tax|_limit)$",
                "desc_pattern": r"(số tiền|giá trị|phí|thuế|hạn mức|dư nợ|chiết khấu)",
                "sql_op": "SUM({col})"
            },
            "DIMENSION": {
                "col_pattern": r"(_type|_status|_channel|_mode|_currency|_state|_method|source_type)$",
                "desc_pattern": r"(loại|trạng thái|kênh|tiền tệ|phương thức|nguồn)",
                "sql_op": "WHERE {col} = '{val}'"
            }
        }

    def _clean_keywords(self, text: str) -> List[str]:
        """Trích xuất từ khóa thô từ mô tả để làm Suggestion cho từ điển"""
        if not isinstance(text, str):
            return []
        
        text = text.lower()
        remove_words = ["là", "của", "người", "dùng", "hệ thống", "ví dụ", "trong", "để"]
        for w in remove_words:
            text = text.replace(f" {w} ", " ")
        
        keywords = []
        matches = re.findall(r"\((.*?)\)", text)
        for m in matches:
            keywords.append(m)
            
        main_phrase = text.split("(")[0].strip()
        keywords.insert(0, main_phrase)
        
        return [k.strip() for k in keywords if len(k) > 2][:3]

    def _detect_role(self, col_name: str, description: str) -> str:

        col_name = col_name.lower()
        description = str(description).lower()

        for role, rule in self.rules.items():

            if re.search(rule["col_pattern"], col_name):
                return role
            
            if re.search(rule["desc_pattern"], description):
                return role

        return "ATTRIBUTE"

    def analyze_file(self, file_path: str, table_name: str = "auto_detect") -> Dict[str, Any]:

        print(f"[*] Đang phân tích file: {file_path}")
        
        if file_path.endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)

        df.columns = [c.strip().lower() for c in df.columns]
        
        col_name_key = next((c for c in df.columns if "tên" in c or "name" in c or "cột" in c), None)
        desc_key = next((c for c in df.columns if "mô tả" in c or "desc" in c), None)

        if not col_name_key:
            raise ValueError("Không tìm thấy cột chứa Tên Cột (Header must contain 'Tên' or 'Name')")

        if table_name == "auto_detect":
            table_name = os.path.splitext(os.path.basename(file_path))[0].split(" - ")[0]

        profile = {
            "table_name": table_name,
            "columns": []
        }

        stats = {"IDENTITY": 0, "METRIC": 0, "DIMENSION": 0, "TEMPORAL": 0, "ATTRIBUTE": 0}

        for _, row in df.iterrows():
            col_raw = str(row[col_name_key]).strip()
            desc_raw = str(row[desc_key]).strip() if desc_key else ""
            
            if not col_raw or col_raw.lower() == "nan":
                continue

            role = self._detect_role(col_raw, desc_raw)
            stats[role] += 1

            suggested_keywords = self._clean_keywords(desc_raw)

            profile["columns"].append({
                "name": col_raw,
                "role": role,
                "description": desc_raw,
                "suggested_keywords": suggested_keywords,
                "sql_logic": self.rules.get(role, {}).get("sql_op", "")
            })

        print(f"Hoàn tất! Table '{table_name}' Stats: {stats}")
        return profile

    def save_profile(self, profile: Dict, output_path: str):
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=4)
        print(f"💾 Đã lưu Profile tại: {output_path}")