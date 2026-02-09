import re
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

sys.path.append(str(Path(__file__).resolve().parent.parent))

from configs.dictionary import COMMON_DICTIONARY
from configs.settings import NER_MODEL_PATH
# from .ner_engine.ner import NER 
# from .ner_engine.vietnamese_time_parser import VietnameseTimeParser

class SchemaRouter:
    def __init__(self, profile_dir):
        if isinstance(profile_dir, str): profile_dir = Path(profile_dir)
        self.parsers: Dict[str, RuleBasedParser] = {}
        self.table_keywords = COMMON_DICTIONARY.get("tables", {})
        self._load_all_profiles(profile_dir)

    def _load_all_profiles(self, profile_dir: Path):
        profile_files = list(profile_dir.glob("*.json"))
        if not profile_files: return
        print(f"[*] Đang tải {len(profile_files)} profile bảng...")
        for p_path in profile_files:
            try:
                parser = RuleBasedParser(str(p_path))
                self.parsers[parser.table_name.lower()] = parser
                print(f"   + Đã load bảng: {parser.table_name.lower()}")
            except Exception as e:
                print(f"   ❌ Lỗi load {p_path.name}: {e}")

    def _detect_table(self, query: str) -> str:
        q_lower = query.lower()
        for table_key, keywords in self.table_keywords.items():
            for kw in keywords:
                if kw in q_lower:
                    if table_key in self.parsers:
                        return table_key
        return None

    def parse(self, query: str):
        target_table = self._detect_table(query)
        if not target_table and "transaction" in self.parsers:
            target_table = "transaction" # Default

        if not target_table:
            return {"error": "Không xác định được bảng", "sql": "", "intent": "UNKNOWN", "detected_table": "N/A"}

        result = self.parsers[target_table].parse(query)
        result["detected_table"] = target_table
        return result

class RuleBasedParser:
    def __init__(self, profile_path: str):
        self.profile = self._load_profile(profile_path)
        self.table_name = self.profile["table_name"]
        
        print(f"   > Init NER cho bảng {self.table_name}...")
        # try: self.time_parser = VietnameseTimeParser()
        # except: self.time_parser = None
        # try: self.ner_engine = NER(model_path=str(NER_MODEL_PATH))
        # except: self.ner_engine = None
        
        self.regex_patterns = {
            "NUMBER": r"\b\d+\b",
            "QUOTED": r"['\"](.*?)['\"]"
        }

    def _load_profile(self, path):
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)

    def _normalize_money(self, text: str) -> str:
        """Biến đổi 5 củ, 10k, 1 triệu thành số nguyên"""
        text = text.lower().replace(",", "").replace(".", "")
        multiplier = 1
        
        if any(w in text for w in ['củ', 'tr', 'triệu', 'm']):
            multiplier = 1_000_000
        elif any(w in text for w in ['k', 'nghìn', 'ngàn']):
            multiplier = 1_000
        elif any(w in text for w in ['tỷ', 'b']):
            multiplier = 1_000_000_000
        elif any(w in text for w in ['lít']): 
            multiplier = 100_000
            
        nums = re.findall(r"\d+", text)
        if nums:
            val = float(nums[0]) * multiplier
            return str(int(val))
        return None

    def _extract_entities_advanced(self, query: str) -> Dict[str, Any]:
        entities = {
            "DATE_RANGE": None, "MONEY": [], "ACCOUNT": [], 
            "BANK": [], "RAW_NUMBERS": [], "QUOTED": []
        }

        if self.time_parser:
            try:
                time_res = self.time_parser.parse(query)
                if time_res and time_res[0] and time_res[1]: 
                    entities["DATE_RANGE"] = time_res 
            except: pass

        if self.ner_engine:
            try:
                ner_res = self.ner_engine.run(query)
                for item in ner_res:
                    label = item['label'] 
                    val = str(item['entity'])
                    
                    if "ACCN" in label or "MONEY" in label:
                        if not any(char.isdigit() for char in val): continue

                    if "MONEY" in label: entities["MONEY"].append(val)
                    elif "ACCN" in label: entities["ACCOUNT"].append(val)
                    elif "BANK" in label: entities["BANK"].append(val)
            except: pass

        slang_pattern = r"(\d+\s*(?:củ|tr|triệu|k|nghìn|ngàn|lít|tỷ))"
        slangs = re.findall(slang_pattern, query.lower())
        for s in slangs:
            money_val = self._normalize_money(s)
            if money_val:
                entities["MONEY"].append(money_val)

        if not entities["ACCOUNT"]:
            all_nums = re.findall(r"\b\d+\b", query)
            for num in all_nums:
                if not any(num in m for m in entities["MONEY"]): 
                     entities["RAW_NUMBERS"].append(num)

        entities["QUOTED"] = re.findall(self.regex_patterns["QUOTED"], query)
        return entities

    def parse(self, question: str) -> Dict[str, Any]:
        intent = "LOOKUP"
        if any(w in question.lower() for w in ["tổng", "số lượng", "bao nhiêu", "thống kê"]):
            intent = "METRIC"
        
        entities = self._extract_entities_advanced(question)
        where_clause = []
        
        if entities["DATE_RANGE"]:
            temp_col = next((c for c in self.profile["columns"] if c["role"] == "TEMPORAL"), None)
            if temp_col:
                start, end = entities["DATE_RANGE"]
                where_clause.append(f"{temp_col['name']} BETWEEN '{start}' AND '{end}'")

        if entities["ACCOUNT"]:
            acc_col = next((c for c in self.profile["columns"] if c["role"] == "IDENTITY"), None)
            if acc_col: where_clause.append(f"{acc_col['name']} = '{entities['ACCOUNT'][0]}'")

        if entities["MONEY"]:
            amt_col = next((c for c in self.profile["columns"] if c["role"] == "METRIC"), None)
            if amt_col: where_clause.append(f"{amt_col['name']} = {entities['MONEY'][0]}")

        if not where_clause and entities["RAW_NUMBERS"]:
            acc_col = next((c for c in self.profile["columns"] if c["role"] == "IDENTITY"), None)
            if acc_col: where_clause.append(f"{acc_col['name']} = '{entities['RAW_NUMBERS'][0]}'")

        if not where_clause:
             return {
                "sql": "", "error": "Không tìm thấy điều kiện lọc",
                "explanation": str(entities), "intent": intent, 
                "detected_table": self.table_name
            }

        select_clause = "*"
        if intent == "METRIC":
            metric_col = next((c for c in self.profile["columns"] if c["role"] == "METRIC"), {"name": "*"})
            select_clause = f"SUM({metric_col['name']})"

        sql = f"SELECT {select_clause} FROM {self.table_name} WHERE {' AND '.join(where_clause)}"
        
        return {
            "sql": sql, "explanation": f"Entities: {entities}",
            "detected_table": self.table_name, "intent": intent, "error": None
        }

import requests
import json

class LlamaSQLEngine:
    def __init__(self, model_name="llama3", base_url="http://localhost:11434/api/generate"):
        self.model_name = model_name
        self.base_url = base_url

    def generate_sql(self, user_query, schema_info, entities):
        # Tạo prompt tối ưu theo kỹ thuật Chain-of-Thought (CoT) trong đặc tả
        prompt = f"""
        Bạn là một AI chuyên gia về SQL. Hãy thực hiện các bước sau:
        1. Phân tích thực thể: {entities}
        2. Dựa trên Schema: {schema_info}
        3. Tạo câu lệnh SQL PostgreSQL cho câu hỏi: "{user_query}"
        
        Lưu ý: Chỉ trả về mã SQL trong khối ```sql ... ```.
        """
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(self.base_url, json=payload)
            result = response.json()
            return result.get("response", "")
        except Exception as e:
            return f"Error connecting to Llama: {e}"

if __name__ == "__main__":
    # llama_engine = LlamaSQLEngine()
    # query = "Lấy tất cả các khách hàng đã đặt hàng trong tháng trước."
    # schema_context = "Bảng Customers (CustomerID, Name, Email), Bảng Orders (OrderID, CustomerID, OrderDate)"
    # entities = ["Customers", "Orders"]
    
    # sql_result = llama_engine.generate_sql(query, schema_context, entities)
    # print(sql_result)
    
    router = SchemaRouter(profile_dir="../data/schema_profiles/")
    
    query = "Tổng số tiền giao dịch của tài khoản 123456 trong hôm nay"
    result = router.parse(query)

    print("--- KẾT QUẢ OUTPUT ---")
    print(f"1. Intent: {result['intent']}")
    print(f"2. Table: {result['detected_table']}")
    print(f"3. Entities: {result['explanation']}")
    print(f"4. SQL generated: {result['sql']}")
