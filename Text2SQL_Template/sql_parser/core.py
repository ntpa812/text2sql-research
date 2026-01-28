import re
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any

sys.path.append(str(Path(__file__).resolve().parent.parent))
from configs.dictionary import COMMON_DICTIONARY

class RuleBasedParser:
    def __init__(self, profile_path: str):
        self.profile = self._load_profile(profile_path)
        self.table_name = self.profile["table_name"]
        self.reverse_index = self._build_reverse_index()
        
        # Regex Patterns
        self.regex_patterns = {
            "DATE": r"(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|hôm nay|hôm qua)",
            "NUMBER": r"\b\d+\b",
            "QUOTED": r"['\"](.*?)['\"]"
        }

    def _load_profile(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _build_reverse_index(self) -> Dict[str, str]:
        index = {}
        # Profile 
        for col in self.profile["columns"]:
            col_name = col["name"]
            index[col_name.lower()] = col_name
            for kw in col.get("suggested_keywords", []):
                if len(kw) > 2: index[kw.lower()] = col_name

        # Dictionary 
        for col in self.profile["columns"]:
            col_name = col["name"].lower()
            if col_name in COMMON_DICTIONARY.get("specific_columns", {}):
                for vn in COMMON_DICTIONARY["specific_columns"][col_name]:
                    index[vn.lower()] = col["name"]
            for suffix, words in COMMON_DICTIONARY.get("suffixes", {}).items():
                if col_name.endswith(suffix):
                    for word in words:
                        if word not in index: index[word.lower()] = col["name"]
        return index

    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        entities = {"DATE": [], "NUMBER": [], "QUOTED": []}
        for key, pattern in self.regex_patterns.items():
            entities[key] = re.findall(pattern, text, re.IGNORECASE)
        return entities

    def _match_column(self, text: str) -> Dict:
        text_lower = text.lower()
        best_match = None
        max_len = 0
        for keyword, col_name in self.reverse_index.items():
            if keyword in text_lower:
                if len(keyword) > max_len:
                    max_len = len(keyword)
                    best_match = next((c for c in self.profile["columns"] if c["name"] == col_name), None)
        return best_match

    def _detect_intent(self, text: str, entities: Dict) -> str:
        text_lower = text.lower()
        if any(k in text_lower for k in ["tổng", "cộng", "thống kê", "bao nhiêu tiền"]):
            return "METRIC"
        if any(k in text_lower for k in ["từ ngày", "đến ngày", "khoảng", "sao kê"]) and entities["DATE"]:
            return "TEMPORAL"
        return "LOOKUP"

    def parse(self, question: str) -> Dict[str, Any]:
        """Core Function: NLQ -> SQL"""
        entities = self._extract_entities(question)
        intent = self._detect_intent(question, entities)
        
        # Clean text 
        clean_text = question
        for key in entities:
            for val in entities[key]:
                clean_text = clean_text.replace(val, "")
        
        target_col = self._match_column(clean_text)
        
        if not target_col:
            if entities["NUMBER"]:
                target_col = next((c for c in self.profile["columns"] if c["role"] == "IDENTITY"), None)
            elif entities["DATE"]:
                target_col = next((c for c in self.profile["columns"] if c["role"] == "TEMPORAL"), None)
        
        if not target_col:
            return {"error": "Không xác định được cột", "sql": ""}

        # Assembly SQL
        sql = ""
        explanation = ""
        col_name = target_col['name']

        if intent == "METRIC":
            sql = f"SELECT SUM({col_name}) FROM {self.table_name}"
            explanation = f"Tính tổng {col_name}"
        elif intent == "TEMPORAL":
            d = entities["DATE"]
            start = d[0]
            end = d[1] if len(d) > 1 else start
            sql = f"SELECT * FROM {self.table_name} WHERE {col_name} BETWEEN '{start}' AND '{end}'"
            explanation = f"Lọc {col_name} từ {start} đến {end}"
        else: 
            val = entities["NUMBER"][0] if entities["NUMBER"] else (entities["QUOTED"][0] if entities["QUOTED"] else "???")
            sql = f"SELECT * FROM {self.table_name} WHERE {col_name} = '{val}'"
            explanation = f"Tra cứu {col_name} = {val}"

        return {
            "question": question,
            "sql": sql,
            "intent": intent,
            "entities": str(entities),
            "target_column": col_name,
            "explanation": explanation
        }