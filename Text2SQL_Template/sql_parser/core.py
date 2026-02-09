import sys
from pathlib import Path
from typing import Dict, List, Any
import requests

# Import module mới vừa tạo
sys.path.append(str(Path(__file__).resolve().parent.parent))
from sql_parser.vector_store import SchemaVectorStore 
from configs.dictionary import COMMON_DICTIONARY
# from .ner_engine.ner import NER 
# from .ner_engine.vietnamese_time_parser import VietnameseTimeParser
import json
import re

BASE_DIR = Path(__file__).resolve().parent.parent

# NER_MODEL_PATH = BASE_DIR / "weights" / "ner_ver2"

class SchemaRouter:
    def __init__(self, profile_dir):
        if isinstance(profile_dir, str): profile_dir = Path(profile_dir)
        self.profile_dir = profile_dir
        self.parsers: Dict[str, LLM_SQL_Parser] = {}
        
        self.vector_store = SchemaVectorStore()
        
        self._load_and_index_profiles()

    def _load_and_index_profiles(self):
        profile_files = list(self.profile_dir.glob("*.json"))
        if not profile_files: return
        
        for p_path in profile_files:
            try:
                parser = LLM_SQL_Parser(str(p_path))
                self.parsers[parser.table_name.lower()] = parser
            except Exception as e:
                print(f"❌ Lỗi load parser {p_path.name}: {e}")
        
        self.vector_store.index_profiles(self.profile_dir)

    def _detect_table(self, query: str) -> str:
        
        result = self.vector_store.search_table(query)    
            
        detected_table = None
        
        if isinstance(result, tuple):
            detected_table = result[0] 
        else:
            detected_table = result

        if detected_table:
            print(f"   => AI chọn bảng: {detected_table}")
            return detected_table.lower()
            
        return None

    def parse(self, query: str):
        target_table = self._detect_table(query)
        
        if not target_table or target_table not in self.parsers:
            return {
                "error": "Không xác định được bảng phù hợp", 
                "sql": "", 
                "intent": "UNKNOWN", 
                "detected_table": "N/A",
                "explanation": "Vector Search did not return a valid table."
            }

        result = self.parsers[target_table].parse(query)
        result["detected_table"] = target_table
        
        if "explanation" not in result:
            result["explanation"] = f"AI routed to table: {target_table}"
        return result

class RuleBasedParser:
    def __init__(self, profile_path: str):
        self.profile = self._load_profile(profile_path)
        self.table_name = self.profile["table_name"]
        
        # print(f"   > Init NER cho bảng {self.table_name}...")
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

        # if self.time_parser:
        #     try:
        #         time_res = self.time_parser.parse(query)
        #         if time_res and time_res[0] and time_res[1]: 
        #             entities["DATE_RANGE"] = time_res 
        #     except: pass

        # if self.ner_engine:
        #     try:
        #         ner_res = self.ner_engine.run(query)
        #         for item in ner_res:
        #             label = item['label'] 
        #             val = str(item['entity'])
                    
        #             if "ACCN" in label or "MONEY" in label:
        #                 if not any(char.isdigit() for char in val): continue

        #             if "MONEY" in label: entities["MONEY"].append(val)
        #             elif "ACCN" in label: entities["ACCOUNT"].append(val)
        #             elif "BANK" in label: entities["BANK"].append(val)
        #     except: pass

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
        


class LLM_SQL_Parser:
    def __init__(self, profile_path: str):
        self.profile = self._load_profile(profile_path)
        self.table_name = self.profile["table_name"]
        
        self.llm_url = "http://localhost:11434/api/generate"
        self.model_name = "llama3:8b" 

    def _load_profile(self, path):
        with open(path, 'r', encoding='utf-8') as f: return json.load(f)

    def _build_schema_context(self) -> str:
        """
        Biến đổi file JSON Profile thành văn bản mô tả để LLM hiểu.
        Tận dụng tối đa trường 'suggested_keywords' và 'description'.
        """
        schema_lines = [f"Table Name: {self.table_name}"]
        
        for col in self.profile.get("columns", []):
            col_name = col["name"]
            col_type = col.get("role", "ATTRIBUTE")
            desc = col.get("description", "")
            
            keywords = ", ".join(col.get("suggested_keywords", []))
            
            val_ref = ""
            if col.get("value_ref"):
                val_ref = f" | Valid Values: {col['value_ref']}"

            line = f"- Column: {col_name} ({col_type})"
            line += f"\n  Desc: {desc}"
            if keywords:
                line += f"\n  Keywords mapping: {keywords}"
            if val_ref:
                line += f"\n {val_ref}"
            
            schema_lines.append(line)
            
        return "\n".join(schema_lines)

    def _call_llm(self, prompt: str):
        """Gửi prompt sang Ollama"""
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1} 
        }
        try:
            response = requests.post(self.llm_url, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json().get("response", "")
            else:
                return f"Error: {response.status_code}"
        except Exception as e:
            return f"Error calling LLM: {str(e)}"

    def parse(self, query: str):
        schema_context = self._build_schema_context()
        
        prompt = f"""
        [ROLE]
        You are an expert SQL Generator for a PostgreSQL database.
        
        [DATABASE SCHEMA]
        {schema_context}
        
        [USER QUESTION]
        "{query}"
        
        [INSTRUCTIONS]
        1. Identify the entities in the question based on the 'Keywords mapping' provided in Schema.
           - Example: If user says "mã tham chiếu", map it to column 'reference_id'.
        2. Generate a valid PostgreSQL query.
        3. Use 'ILIKE' for text comparison if unsure about case sensitivity.
        4. ONLY return the SQL query inside a code block ```sql ... ```. Do not explain.
        
        [ANSWER]
        """
        
        print(f"   🤖 Sending prompt to LLM for table '{self.table_name}'...")
        
        # 3. Gọi LLM
        llm_response = self._call_llm(prompt)
        
        sql = llm_response
        if "```sql" in llm_response:
            sql = llm_response.split("```sql")[1].split("```")[0].strip()
        elif "```" in llm_response:
            sql = llm_response.split("```")[1].split("```")[0].strip()
            
        return {
            "sql": sql,
            "explanation": "Generated by LLM based on Schema Keywords",
            "detected_table": self.table_name,
            "intent": "GENERATED"
        } 