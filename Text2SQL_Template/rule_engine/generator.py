import json
import itertools
import random
from typing import List, Dict, Any, Tuple
from pathlib import Path
import pandas as pd
import re

from configs.dictionary import COMMON_DICTIONARY
from .faker_utils import DataFaker
from .grammar_templates import GrammarLibrary

class RuleBasedGenerator:
    def __init__(self):
        self.faker = DataFaker()
        self.grammar = GrammarLibrary()
        self.vocab = COMMON_DICTIONARY

        self.sql_templates = {
            "IDENTITY": "SELECT * FROM {table} WHERE {col} = '{{{{{col}}}}}'",
            "DIMENSION": "SELECT * FROM {table} WHERE {col} = '{{{{{col}}}}}'",
            "METRIC_SUM": "SELECT SUM({col}) FROM {table} WHERE {dim_col} = '{{{{{dim_col}}}}}'",
            "TEMPORAL": "SELECT * FROM {table} WHERE {col} BETWEEN '{{{{start_date}}}}' AND '{{{{end_date}}}}' ORDER BY {col} DESC",
            "MIX_TYPE_AMOUNT": "SELECT * FROM {table} WHERE {type_col} = '{{{{{type_col}}}}}' AND {amt_col} > {{{{{amt_col}}}}} AND {status_col} = 'SUCCESS'",
            "MIX_FULL": "SELECT * FROM {table} WHERE {type_col} = '{{{{{type_col}}}}}' AND {amt_col} > {{{{{amt_col}}}}} AND {time_col} BETWEEN '{{{{start_date}}}}' AND '{{{{end_date}}}}' AND {status_col} = 'SUCCESS'"
        }

    def _classify_column(self, col_name: str) -> str:
        col = col_name.lower()
        
        if col in ["trans_id", "id", "transaction_id"]: return "PRIMARY_ID"
        if any(x in col for x in ["ref", "parent", "original"]): return "REF_ID"
        if any(x in col for x in ["user_id", "node", "session", "maker", "checker", "trace"]): return "TECH_ID"
        if any(x in col for x in ["cif", "cust", "user","cust_id", "customer_id"]): return "CUST_ID"
        
        return "OTHER"

    def _get_synonyms(self, col_name: str, suggested: List[str]) -> List[str]:
        col_lower = col_name.lower()
        # Use a list to preserve order (Priority: Specific -> Generated -> Suggested)
        synonyms = [] 
        seen = set() # To track duplicates

        # 1. Specific Column (Highest Priority)
        if col_lower in self.vocab.get("specific_columns", {}):
            for word in self.vocab["specific_columns"][col_lower]:
                if word not in seen:
                    synonyms.append(word)
                    seen.add(word)
            return synonyms # Return immediately if specific match found

        # 2. Semantic Generation (Suffix + Prefix)
        parts = col_lower.split('_')
        suffix_match = None
        suffix_meanings = []

        # logic to find suffix...
        possible_suffix = "_" + parts[-1]
        if possible_suffix in self.vocab.get("suffixes", {}):
            suffix_match = possible_suffix
            suffix_meanings = self.vocab["suffixes"][possible_suffix]
            core_parts = parts[:-1]
        else:
            core_parts = parts

        # logic to translate prefix...
        translated_parts = []
        col_mapping = self.vocab.get("col_mapping", {})
        tables = self.vocab.get("tables", {}) # Don't forget tables fallback

        for part in core_parts:
            if part in col_mapping:
                translated_parts.append(col_mapping[part][0])
            elif part in tables:
                translated_parts.append(tables[part][0])
            else:
                pass # Or keep original part? pass is safer for pure translation

        # Construct phrases
        generated_phrases = []
        if suffix_meanings:
            base_suffix = suffix_meanings[0]
            core_meaning = " ".join(translated_parts)
            if core_meaning:
                generated_phrases.append(f"{base_suffix} {core_meaning}".strip()) # "trạng thái giao dịch"
                generated_phrases.append(f"{core_meaning}".strip()) # "giao dịch" (contextual)
        else:
            full_meaning = " ".join(translated_parts).strip()
            if full_meaning:
                generated_phrases.append(full_meaning)

        # Add generated phrases to main list
        for phrase in generated_phrases:
            if phrase and phrase not in seen:
                synonyms.append(phrase)
                seen.add(phrase)

        # 3. Suggested Keywords (Lowest Priority - can contain garbage)
        if suggested:
            clean = [s for s in suggested if len(s.split()) < 6 and "khóa" not in s.lower()]
            for s in clean:
                if s not in seen:
                    synonyms.append(s)
                    seen.add(s)

        # Fallback
        if not synonyms:
            synonyms.append(col_lower.replace("_", " "))

        return synonyms
    
    def _get_table_synonyms(self, table_name: str) -> List[str]:
        return self.vocab["tables"].get(table_name, [table_name])

    def _generate_natural_queries(self, group_type: str, context: Dict) -> List[str]:
        
        noun = context.get('noun', 'giao dịch')
        col_vn = context.get('col_name', '')
        val = context.get('fake_val', '')
        
        queries = set()
        
        time_suffixes = [" hôm nay", " hôm qua", " tuần này", ""]
        status_suffixes = [" xem thành công chưa", " đang ở trạng thái nào", " chi tiết", ""]
        
        if group_type == "PRIMARY_ID":
            
            suffix_t = random.choice(time_suffixes)
            suffix_s = random.choice(status_suffixes)
            
            queries.add(f"Tra cứu {noun} {val}{suffix_t}")
            queries.add(f"Kiểm tra lệnh {val}{suffix_s}")
            queries.add(f"Xem chi tiết {noun} số {val}")
            queries.add(f"Check giao dịch {val}")
        
        elif group_type == "REF_ID":
            queries.add(f"Tìm {noun} có {col_vn} là {val}")
            queries.add(f"Tra soát theo {col_vn} {val}")
            queries.add(f"Check {col_vn} {val} giúp em")
            
        elif group_type == "CUST_ID":
            queries.add(f"Liệt kê giao dịch của khách hàng {val}")
            queries.add(f"Xem lịch sử của {col_vn} {val}")
            queries.add(f"Sao kê cho {col_vn} {val}")

        elif group_type == "DIMENSION":
            col_raw = context.get('col_raw', '').lower()
            vocab_values = self.vocab.get("values", {})
            target_group = {}
            
            if "status" in col_raw: target_group = vocab_values.get("STATUS", {})
            elif any(x in col_raw for x in ["channel", "kenh"]): target_group = vocab_values.get("CHANNEL", {})
            elif any(x in col_raw for x in ["type", "code", "service"]): target_group = vocab_values.get("TRANS_TYPE", {})

            if target_group:
                keys = list(target_group.keys())
                sampled_keys = random.sample(keys, min(3, len(keys)))
                
                for k in sampled_keys:
                    adj = random.choice(target_group[k]) # VD: "thất bại"
                    queries.add(f"{noun} {adj}")  # "giao dịch thất bại"
                    queries.add(f"danh sách {noun} {adj}")
                    queries.add(f"lọc các {noun} đang {adj}")
            else:
                queries.add(f"Lọc {noun} theo {col_vn} {val}")
                queries.add(f"Danh sách {noun} có {col_vn} là {val}")

        return list(queries)

    def generate_dataset(self, profile_path: str) -> List[Dict]:
        print(f"[*] Đang xử lý profile: {profile_path}")
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)
            
        table_name = profile["table_name"]
        columns = profile["columns"]
        dataset = []

        cols_by_role = {"IDENTITY": [], "DIMENSION": [], "METRIC": [], "TEMPORAL": []}
        spec_cols = {"amount": None, "status": None, "type": None, "date": None}

        for col in columns:
            if col["role"] in cols_by_role:
                cols_by_role[col["role"]].append(col)
            c_name = col["name"].lower()
            if "amount" in c_name or "amt" in c_name: spec_cols["amount"] = col
            if "status" in c_name or "trang_thai" in c_name: spec_cols["status"] = col
            if "type" in c_name or "service" in c_name: spec_cols["type"] = col
            if col["role"] == "TEMPORAL": spec_cols["date"] = col

        table_syns = self._get_table_synonyms(table_name)
        main_noun = table_syns[0]

        for col in columns:
            role = col["role"]
            col_raw = col["name"]
            
            group_type = "OTHER"
            if role == "IDENTITY":
                group_type = self._classify_column(col_raw)
                if group_type == "TECH_ID": 
                    continue 

            elif role == "DIMENSION":
                group_type = "DIMENSION"

            col_syns = self._get_synonyms(col_raw, col["suggested_keywords"])
            primary_col_name = col_syns[0]
            
            fake_val = self.faker.get_fake_value(col_raw, role)
            
            context = {
                "noun": main_noun, "col_name": primary_col_name,
                "col_raw": col_raw, "role": role,
                "fake_val": fake_val
            }
            
            qs = []
            
            if role == "IDENTITY":
                sql = self.sql_templates["IDENTITY"].format(table=table_name, col=col_raw)
                qs = self._generate_natural_queries(group_type, context)
                
                doc = f"{table_name} | Tra cứu {primary_col_name}"
                desc = f"Tìm kiếm chính xác theo {primary_col_name}"
                kw = ", ".join(col_syns)
                
                if qs: 
                    dataset.append({"document": doc, "description": desc, "sql": sql, "examples": qs, "keyword": kw})

            elif role == "DIMENSION":
                status_clause = ""
                if spec_cols["status"] and col_raw != spec_cols["status"]["name"] and "status" not in col_raw.lower():
                    status_clause = f" AND {spec_cols['status']['name']} = 'SUCCESS'"
                
                sql = self.sql_templates["DIMENSION"].format(table=table_name, col=col_raw) + status_clause
                
                qs = self._generate_natural_queries("DIMENSION", context)
                
                doc = f"{table_name} | Lọc theo {primary_col_name}"
                desc = f"Phân nhóm giao dịch theo {primary_col_name}"
                kw = ", ".join(col_syns)
                
                if qs:
                    dataset.append({"document": doc, "description": desc, "sql": sql, "examples": qs, "keyword": kw})

            elif role == "METRIC":
                sql = f"SELECT SUM({col_raw}) FROM {table_name}"
                if spec_cols["status"]: sql += f" WHERE {spec_cols['status']['name']} = 'SUCCESS'"
                
                qs = [
                    f"Tổng {primary_col_name} là bao nhiêu?",
                    f"Tính tổng {primary_col_name} của các giao dịch thành công",
                    f"Thống kê {primary_col_name} hôm nay"
                ]
                
                dataset.append({
                    "document": f"{table_name} | Thống kê {primary_col_name}", 
                    "description": f"Tính tổng giá trị {primary_col_name}", 
                    "sql": sql, "examples": qs, "keyword": "tổng, thống kê"
                })

            elif role == "TEMPORAL":
                sql = self.sql_templates["TEMPORAL"].format(table=table_name, col=col_raw)
                
                start_d = self.faker._generate_date(range_days=60)
                end_d = self.faker._generate_date(range_days=0)
                
                qs = [
                    f"Sao kê {main_noun} theo {primary_col_name} từ ngày {start_d} đến ngày {end_d}",
                    f"Lọc {main_noun} có {primary_col_name} trong khoảng {start_d} - {end_d}",
                    f"Xem lịch sử {main_noun} dựa trên {primary_col_name} từ {start_d} tới {end_d}",
                    f"Kiểm tra các {main_noun} với {primary_col_name} là ngày {start_d}"
                ]

                dataset.append({
                    "document": f"{table_name} | Lọc thời gian theo {primary_col_name}", 
                    "description": f"Truy vấn lịch sử dựa trên cột {primary_col_name}", 
                    "sql": sql, 
                    "examples": qs, 
                    "keyword": f"thời gian, lịch sử, {primary_col_name}"
                })

        if spec_cols["type"] and spec_cols["amount"] and spec_cols["status"]:
            type_c = spec_cols["type"]["name"]
            amt_c = spec_cols["amount"]["name"]
            stt_c = spec_cols["status"]["name"]
            sql_mix = self.sql_templates["MIX_TYPE_AMOUNT"].format(table=table_name, type_col=type_c, amt_col=amt_c, status_col=stt_c)
            
            qs_mix = []
            type_vals = self.faker.dict_type
            if type_vals:
                key = random.choice(list(type_vals.keys()))
                adj = random.choice(type_vals[key])
                amt = self.faker._generate_amount()
                qs_mix.append(f"{main_noun} {adj} trên {amt}")
                qs_mix.append(f"Tìm các {main_noun} {adj} > {amt}")
            
            dataset.append({
                "document": f"{table_name} | Lọc Loại + Số tiền",
                "description": "Lọc nâng cao: Loại giao dịch + Số tiền tối thiểu",
                "sql": sql_mix,
                "examples": qs_mix,
                "keyword": "lọc nâng cao"
            })

        print(f"Đã sinh {len(dataset)} logic truy vấn cho bảng {table_name}\n")
        return dataset

    def export_excel(self, dataset: List[Dict], output_path: str):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for item in dataset:
            rows.append({
                "document": item["document"],
                "description": item["description"],
                "examples": "\n".join(item["examples"]),
                "keyword": item["keyword"],
                "metadata": json.dumps({"raw_text": item["sql"]}, ensure_ascii=False)
            })
        df = pd.DataFrame(rows)
        try:
            df.to_excel(output_path, index=False)
            print(f"💾 Kết quả lưu tại: {output_path}")
        except Exception as e:
            print(f"❌ Lỗi lưu file: {e}")