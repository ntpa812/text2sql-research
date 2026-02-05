import json
import random
from typing import List, Dict
from pathlib import Path
import pandas as pd

from configs.dictionary import COMMON_DICTIONARY
from .faker_utils import DataFaker
from .grammar_templates import GrammarLibrary

class RuleBasedGenerator:
    def __init__(self, vocab=None):
        self.faker = DataFaker()
        self.grammar = GrammarLibrary()
        
        if vocab:
            self.vocab = vocab
        else:
            try:
                from configs.dictionary import COMMON_DICTIONARY
                self.vocab = COMMON_DICTIONARY
            except ImportError:
                self.vocab = {}

        self.sql_templates = {
            "IDENTITY": "SELECT * FROM {table} WHERE {col} = '{{{{{col}}}}}'",
            "DIMENSION": "SELECT * FROM {table} WHERE {col} = '{{{{{col}}}}}'",
            "METRIC_SUM": "SELECT SUM({col}) FROM {table} WHERE {dim_col} = '{{{{{dim_col}}}}}'",
            "TEMPORAL": "SELECT * FROM {table} WHERE {col} BETWEEN '{{{{start_date}}}}' AND '{{{{end_date}}}}' ORDER BY {col} DESC",
            "MIX_TYPE_AMOUNT": "SELECT * FROM {table} WHERE {type_col} = '{{{{{type_col}}}}}' AND {amt_col} > {{{{{amt_col}}}}} AND {status_col} = 'SUCCESS'"
        }

    def _get_table_synonyms(self, table_name):
        return self.vocab.get("tables", {}).get(table_name, [table_name])

    def _get_synonyms(self, col_raw, suggested=None):
        base_syns = self.vocab.get("specific_columns", {}).get(col_raw.lower(), [])
        if suggested:
            base_syns.extend(suggested)
        if not base_syns:
            base_syns = [col_raw]
        return list(set(base_syns))

    def _classify_column(self, col_name):
        col_name = col_name.lower()
        if any(x in col_name for x in ["id", "key", "guid", "uuid"]) and "customer" not in col_name and "trans" not in col_name:
            return "TECH_ID"
        return "BUSINESS_ID"

    def _generate_natural_queries(self, group_type: str, context: Dict) -> List[str]:
        templates = self.grammar.get_templates(group_type)
        if not templates: return []

        generated_qs = set()
        
        verbs = self.vocab.get("verbs", {}).get("lookup", ["Tìm", "Tra cứu", "Hiển thị"])
        filters = self.vocab.get("verbs", {}).get("filter", ["Lọc", "Liệt kê"])
        all_action_verbs = verbs + filters
        
        time_suffixes = [" hôm nay", " hôm qua", " tuần này", ""]
        status_suffixes = [" xem thành công chưa", " đang ở trạng thái nào", " chi tiết", ""]

        val_ref = context.get('value_ref')
        vocab_values = self.vocab.get("values", {})
        
        target_group = {}
        if val_ref and val_ref in vocab_values:
            target_group = vocab_values[val_ref]

        if target_group and group_type == "DIMENSION":
            keys = list(target_group.keys())
            sampled_keys = random.sample(keys, min(3, len(keys)))
            noun = context.get('noun', '')

            for k in sampled_keys:
                adj_list = target_group[k]
                if not adj_list: continue
                adj = random.choice(adj_list)
                v = random.choice(all_action_verbs)
                
                generated_qs.add(f"{noun} {adj}")
                generated_qs.add(f"{v} các {noun} {adj}")
                generated_qs.add(f"{v} danh sách {noun} là {adj}")

        for tmpl in templates:
            if group_type == "DIMENSION":
                chosen_verb = random.choice(all_action_verbs)
            elif group_type == "CUST_ID":
                chosen_verb = random.choice(filters)
            else:
                chosen_verb = random.choice(verbs)

            chosen_suffix = ""
            if group_type == "IDENTITY":
                chosen_suffix = random.choice(time_suffixes + status_suffixes)

            try:
                q = tmpl.format(
                    verb=chosen_verb, 
                    suffix=chosen_suffix,
                    **context
                )
                q = " ".join(q.split())
                generated_qs.add(q)
            except KeyError:
                continue
                
        return list(generated_qs)

    def generate_dataset(self, profile_path: str) -> List[Dict]:
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)
            
        table_name = profile["table_name"]
        columns = profile["columns"]
        dataset = []

        seen_keys = set()
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
            
            if col_raw in seen_keys:
                continue
            seen_keys.add(col_raw)
            
            group_type = "OTHER"
            if role == "IDENTITY":
                if self._classify_column(col_raw) == "TECH_ID": 
                    continue
                group_type = "IDENTITY"

            elif role == "DIMENSION":
                group_type = "DIMENSION"

            col_syns = self._get_synonyms(col_raw, col.get("suggested_keywords", []))
            primary_col_name = col_syns[0] if col_syns else col_raw
            
            val = self.faker.get_fake_value(col_raw, role)
            
            context = {
                "noun": main_noun, 
                "col_name": primary_col_name,
                "col_raw": col_raw, 
                "role": role,
                "val": val,
                "value_ref": col.get("value_ref")
            }
            
            qs = []
            
            if role == "IDENTITY":
                sql = self.sql_templates["IDENTITY"].format(table=table_name, col=col_raw)
                qs = self._generate_natural_queries("IDENTITY", context)
                
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
                    f"Tính tổng {primary_col_name}",
                    f"Thống kê {primary_col_name} hôm nay"
                ]
                
                dataset.append({
                    "document": f"{table_name} | Thống kê {primary_col_name}", 
                    "description": f"Tính tổng giá trị {primary_col_name}", 
                    "sql": sql, "examples": qs, "keyword": f"tổng, thống kê, theo {primary_col_name}"
                })

            elif role == "TEMPORAL":
                sql = self.sql_templates["TEMPORAL"].format(table=table_name, col=col_raw)
                start_d = self.faker._generate_date(range_days=60)
                end_d = self.faker._generate_date(range_days=0)
                
                qs = [
                    f"Sao kê {main_noun} theo {primary_col_name} từ ngày {start_d} đến ngày {end_d}",
                    f"Lọc {main_noun} có {primary_col_name} trong khoảng {start_d} - {end_d}",
                    f"Xem lịch sử {main_noun} dựa trên {primary_col_name} từ {start_d} tới {end_d}"
                ]

                dataset.append({
                    "document": f"{table_name} | Lọc thời gian theo {primary_col_name}", 
                    "description": f"Truy vấn lịch sử dựa trên cột {primary_col_name}", 
                    "sql": sql, "examples": qs, "keyword": f"thời gian, lịch sử, {primary_col_name}"
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