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
            "ATTRIBUTE": "SELECT * FROM {table} WHERE {col} LIKE '%{{{{{col}}}}}%'",
            
            # Complex Intents
            "MULTI_DIM_TIME": "SELECT * FROM {table} WHERE {dim_col} = '{{{{{dim_col}}}}}' AND {time_col} BETWEEN '{{{{start_date}}}}' AND '{{{{end_date}}}}'",
            "MIX_TYPE_AMOUNT": "SELECT * FROM {table} WHERE {type_col} = '{{{{{type_col}}}}}' AND {amt_col} > {{{{{amt_col}}}}} AND {status_col} = 'SUCCESS'",
            "MIX_FULL": "SELECT * FROM {table} WHERE {type_col} = '{{{{{type_col}}}}}' AND {amt_col} > {{{{{amt_col}}}}} AND {time_col} BETWEEN '{{{{start_date}}}}' AND '{{{{end_date}}}}' AND {status_col} = 'SUCCESS'"
        }

    def _get_synonyms(self, col_name: str, suggested: List[str]) -> List[str]:
        synonyms = set(suggested)
        col_lower = col_name.lower()

        if col_lower in self.vocab.get("specific_columns", {}):
            synonyms.update(self.vocab["specific_columns"][col_lower])
            return list(synonyms)

        for suffix, words in self.vocab.get("suffixes", {}).items():
            if col_lower.endswith(suffix):
                synonyms.update(words)

        if not synonyms:
            synonyms.add(col_name)
        return list(synonyms)

    def _get_table_synonyms(self, table_name: str) -> List[str]:
        if table_name in self.vocab["tables"]:
            return self.vocab["tables"][table_name]
        return [table_name]

    def _generate_examples(self, intent_code: str, context: Dict) -> List[str]:

        raw_templates = self.grammar.get_templates(intent_code)
        examples = set()
        
        verbs = ["Tra cứu", "Tìm", "Xem"]
        if "METRIC" in intent_code: verbs = ["Tính tổng", "Thống kê", "Tổng hợp"]
        
        for tpl in raw_templates:
            fake_val = self.faker.get_fake_value(context.get('col_raw', ''), context.get('role', 'ATTRIBUTE'))
            fake_start = self.faker._generate_date(30)
            fake_end = "hôm nay"
            
            noun_str = context.get('noun') or "giao dịch"
            col_name_str = context.get('col_name') or "giá trị"
            
            q_std = self.grammar.format_template(
                tpl,
                verb=random.choice(verbs),
                # noun=context.get('noun', 'bản ghi'),
                # col_name=context.get('col_name', ''),
                noun=noun_str,         
                col_name=col_name_str,
                col_metric=context.get('col_metric', ''),
                col_group=context.get('col_group', ''),
                val=fake_val,
                start=fake_start,
                end=fake_end,
                amt_val=self.faker._generate_amount(),
                type_val=self.faker.get_fake_value("trans_type", "DIMENSION")
            )
            examples.add(q_std)

        if intent_code in ["DIMENSION", "MIX_TYPE_AMOUNT", "MIX_FULL"]:
            col = context.get('col_raw', '').lower()
            vocab_values = self.vocab.get("values", {})
            
            target_group = {}
            if "status" in col: target_group = vocab_values.get("STATUS", {})
            elif "channel" in col: target_group = vocab_values.get("CHANNEL", {})
            elif any(x in col for x in ["type", "code", "service"]): target_group = vocab_values.get("TRANS_TYPE", {})
            
            if "MIX" in intent_code:
                 target_group = vocab_values.get("TRANS_TYPE", {})

            if target_group:
                random_key = random.choice(list(target_group.keys()))
                adjectives = target_group[random_key]
                if adjectives:
                    adj = random.choice(adjectives)
                    noun = context['noun']
                    if intent_code == "DIMENSION":
                        examples.add(f"{noun} {adj}")
                        examples.add(f"danh sách {noun} {adj}")
                    elif intent_code == "MIX_TYPE_AMOUNT":
                        amt = self.faker._generate_amount()
                        examples.add(f"{noun} {adj} trên {amt}")
                        examples.add(f"tìm {noun} {adj} > {amt}")
                    elif intent_code == "MIX_FULL":
                        amt = self.faker._generate_amount()
                        examples.add(f"{noun} {adj} trên {amt} hôm qua")

        return list(examples)

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
            col_syns = self._get_synonyms(col_raw, col["suggested_keywords"])
            primary_col_name = col_syns[0]
            
            context = {
                "noun": main_noun, "col_name": primary_col_name,
                "col_raw": col_raw, "role": role
            }
            
            record = None
            
            # Logic Default Status = SUCCESS
            status_clause = ""
            if spec_cols["status"] and col_raw != spec_cols["status"]["name"]:
                status_clause = f" AND {spec_cols['status']['name']} = 'SUCCESS'"

            if role == "IDENTITY":
                sql = self.sql_templates["IDENTITY"].format(table=table_name, col=col_raw)
                qs = self._generate_examples("IDENTITY", context)
                
                doc = f"{table_name} | Tra cứu theo {primary_col_name}"

                desc = f"Tìm kiếm chính xác thông tin {main_noun} dựa trên {primary_col_name} ({col_raw})"

                kw = ", ".join(col_syns)
                
                record = {"document": doc, "description": desc, "sql": sql, "examples": qs, "keyword": kw}

            elif role == "DIMENSION":
                current_sql = self.sql_templates["DIMENSION"].format(table=table_name, col=col_raw)
                if "status" not in col_raw.lower():
                    current_sql += status_clause

                qs = self._generate_examples("DIMENSION", context)
                
                doc = f"{table_name} | Lọc theo {primary_col_name}"
                desc = f"Liệt kê danh sách {main_noun} được phân nhóm bởi {primary_col_name}. Ví dụ: {primary_col_name} A, B..."
                kw = ", ".join(col_syns)
                
                record = {"document": doc, "description": desc, "sql": current_sql, "examples": qs, "keyword": kw}

            elif role == "METRIC":
                sql = f"SELECT SUM({col_raw}) FROM {table_name}"
                if spec_cols["status"]:
                    sql += f" WHERE {spec_cols['status']['name']} = 'SUCCESS'"
                
                target_dim = cols_by_role["DIMENSION"][0]["name"] if cols_by_role["DIMENSION"] else "..."
                
                qs = self._generate_examples("METRIC", context)
                
                doc = f"{table_name} | Thống kê {primary_col_name}"
                desc = f"Tính tổng giá trị {primary_col_name} của {main_noun}. Có thể kết hợp điều kiện lọc (Mặc định chỉ tính giao dịch thành công)."
                kw = ", ".join(col_syns)
                
                record = {"document": doc, "description": desc, "sql": sql, "examples": qs, "keyword": kw}

            elif role == "TEMPORAL":
                sql = self.sql_templates["TEMPORAL"].format(table=table_name, col=col_raw)
                qs = self._generate_examples("TEMPORAL", context)
                
                doc = f"{table_name} | Lọc theo thời gian ({primary_col_name})"
                desc = f"Truy vấn lịch sử {main_noun} trong một khoảng thời gian cụ thể (Từ ngày... đến ngày...)"
                kw = ", ".join(col_syns + ["thời gian", "ngày tháng", "lịch sử", "gần đây"])
                
                record = {"document": doc, "description": desc, "sql": sql, "examples": qs, "keyword": kw}
            
            elif role == "ATTRIBUTE":
                
                sql = f"SELECT * FROM {table_name} WHERE {col_raw} LIKE '%{{{{{col_raw}}}}}%'"
                
                qs = self._generate_examples("IDENTITY", context) 
                
                doc = f"{table_name} | Tìm kiếm theo {primary_col_name}"
                desc = f"Tìm kiếm các {main_noun} có chứa nội dung/từ khóa trong {primary_col_name}"
                kw = ", ".join(col_syns)
                
                record = {"document": doc, "description": desc, "sql": sql, "examples": qs, "keyword": kw}
                
            if record: dataset.append(record)

        if spec_cols["type"] and spec_cols["amount"] and spec_cols["status"]:
            type_c = spec_cols["type"]["name"]
            amt_c = spec_cols["amount"]["name"]
            stt_c = spec_cols["status"]["name"]
            
            sql_mix = self.sql_templates["MIX_TYPE_AMOUNT"].format(table=table_name, type_col=type_c, amt_col=amt_c, status_col=stt_c)
            ctx_mix = {"noun": main_noun, "col_name": "loại và tiền", "col_raw": type_c, "role": "DIMENSION"}
            qs_mix = self._generate_examples("MIX_TYPE_AMOUNT", ctx_mix)
            
            dataset.append({
                "document": f"{table_name} | Lọc Loại + Số tiền (Nâng cao)",
                "description": f"Tìm các {main_noun} thỏa mãn cùng lúc 2 điều kiện: Loại giao dịch cụ thể VÀ Số tiền lớn hơn mức X (Chỉ lấy trạng thái Success)",
                "sql": sql_mix,
                "examples": qs_mix,
                "keyword": "loại và tiền, giao dịch lớn, chi tiết"
            })

        if spec_cols["type"] and spec_cols["amount"] and spec_cols["date"] and spec_cols["status"]:
            type_c = spec_cols["type"]["name"]
            amt_c = spec_cols["amount"]["name"]
            time_c = spec_cols["date"]["name"]
            stt_c = spec_cols["status"]["name"]
            
            sql_full = self.sql_templates["MIX_FULL"].format(table=table_name, type_col=type_c, amt_col=amt_c, time_col=time_c, status_col=stt_c)
            qs_full = self._generate_examples("MIX_FULL", ctx_mix)
            
            dataset.append({
                "document": f"{table_name} | Lọc Full: Loại + Tiền + Thời gian",
                "description": f"Truy vấn phức tạp nhất: Kết hợp Loại giao dịch + Mức tiền tối thiểu + Khoảng thời gian. Dùng để báo cáo chi tiết.",
                "sql": sql_full,
                "examples": qs_full,
                "keyword": "báo cáo chi tiết, tổng hợp"
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
        import time
        try:
            df.to_excel(output_path, index=False)
            print(f"💾 Kết quả lưu tại: {output_path}")
        except Exception as e:
            print(f"❌ Lỗi lưu file: {e}")