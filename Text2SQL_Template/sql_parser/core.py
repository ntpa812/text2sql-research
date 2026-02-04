import re
import json
import sys
from pathlib import Path
from typing import Dict, List, Any

# Setup path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from configs.dictionary import COMMON_DICTIONARY
from configs.settings import NER_MODEL_PATH
from .ner_engine.ner import NER 
from .ner_engine.vietnamese_time_parser import VietnameseTimeParser

class SchemaRouter:
    # ... (Giữ nguyên phần Router như cũ không thay đổi) ...
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
        try: self.time_parser = VietnameseTimeParser()
        except: self.time_parser = None
        try: self.ner_engine = NER(model_path=str(NER_MODEL_PATH))
        except: self.ner_engine = None
        
        # Regex cơ bản
        self.regex_patterns = {
            "NUMBER": r"\b\d+\b",
            "QUOTED": r"['\"](.*?)['\"]"
        }

    def _load_profile(self, path):
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)

    # --- HÀM MỚI: CHUẨN HÓA TIỀN TỆ (Gánh cho model dởm) ---
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
        elif any(w in text for w in ['lít']): # Tiếng lóng: 1 lít = 100k
            multiplier = 100_000
            
        # Lấy số đầu tiên tìm thấy
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

        # 1. Time Parser
        if self.time_parser:
            try:
                time_res = self.time_parser.parse(query)
                if time_res and time_res[0] and time_res[1]: 
                    entities["DATE_RANGE"] = time_res 
            except: pass

        # 2. NER Model (Vẫn chạy để bắt các case chuẩn)
        if self.ner_engine:
            try:
                ner_res = self.ner_engine.run(query)
                for item in ner_res:
                    label = item['label'] 
                    val = str(item['entity'])
                    
                    # Bộ lọc rác
                    if "ACCN" in label or "MONEY" in label:
                        if not any(char.isdigit() for char in val): continue

                    if "MONEY" in label: entities["MONEY"].append(val)
                    elif "ACCN" in label: entities["ACCOUNT"].append(val)
                    elif "BANK" in label: entities["BANK"].append(val)
            except: pass

        # 3. MANUAL REGEX FOR SLANG (Cứu cánh khi Model trượt)
        # Tìm các pattern kiểu: 5 củ, 10k, 500 nghìn...
        slang_pattern = r"(\d+\s*(?:củ|tr|triệu|k|nghìn|ngàn|lít|tỷ))"
        slangs = re.findall(slang_pattern, query.lower())
        for s in slangs:
            money_val = self._normalize_money(s)
            if money_val:
                # Thêm vào danh sách MONEY và không coi là RAW_NUMBER nữa
                entities["MONEY"].append(money_val)

        # 4. Fallback Regex (Chỉ lấy số trơ trọi còn lại làm Account/ID)
        if not entities["ACCOUNT"]:
            # Logic: Tìm số, nhưng loại bỏ những số đã được nhận diện là Tiền ở bước 3
            all_nums = re.findall(r"\b\d+\b", query)
            for num in all_nums:
                # Nếu số này chưa nằm trong danh sách tiền đã xử lý
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
        
        # --- Mapping ---
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

        # Fallback: Nếu có RAW_NUMBER mà chưa map vào Account (ưu tiên gán số dài vào Account)
        if not where_clause and entities["RAW_NUMBERS"]:
            # Lấy số đầu tiên làm account
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