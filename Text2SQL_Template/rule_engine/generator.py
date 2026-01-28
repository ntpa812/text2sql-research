import json
import itertools
from typing import List, Dict, Any, Tuple
from pathlib import Path
import pandas as pd

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
            
            "MULTI_DIM_TIME": "SELECT * FROM {table} WHERE {dim_col} = '{{{{{dim_col}}}}}' AND {time_col} BETWEEN '{{{{start_date}}}}' AND '{{{{end_date}}}}'"
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
        
        parts = table_name.split('_')
        for part in parts:
            if part in self.vocab["tables"]:
                return self.vocab["tables"][part]
                
        return [table_name] # Fallback

    def _generate_examples(self, intent_code: str, context: Dict) -> List[str]:
        
        raw_templates = self.grammar.get_templates(intent_code)
        examples = set()
        
        verbs = ["Tra cứu", "Tìm", "Xem"] # Default
        if intent_code == "METRIC": verbs = ["Tính tổng", "Thống kê"]
        
        for tpl in raw_templates:

            fake_val = self.faker.get_fake_value(context.get('col_raw', ''), context.get('role', 'ATTRIBUTE'))
            fake_start = self.faker._generate_date(30) 
            fake_end = "hôm nay"
            
            q_real = self.grammar.format_template(
                tpl,
                verb=verbs[0],
                noun=context['noun'],
                col_name=context['col_name'],
                col_metric=context.get('col_metric', ''),
                col_group=context.get('col_group', ''),
                val=fake_val,
                start=fake_start,
                end=fake_end
            )
            examples.add(q_real)

        return list(examples)

    def generate_dataset(self, profile_path: str) -> List[Dict]:
        print(f"[*] Đang xử lý profile: {profile_path}")
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)
            
        table_name = profile["table_name"]
        columns = profile["columns"]
        
        dataset = []
        
        cols_by_role = {
            "IDENTITY": [], "DIMENSION": [], "METRIC": [], "TEMPORAL": []
        }
        for col in columns:
            if col["role"] in cols_by_role:
                cols_by_role[col["role"]].append(col)

        table_syns = self._get_table_synonyms(table_name)
        main_noun = table_syns[0]

        # SINGLE COLUMN LOGIC 
        for col in columns:
            role = col["role"]
            col_raw = col["name"]
            col_syns = self._get_synonyms(col_raw, col["suggested_keywords"])
            primary_col_name = col_syns[0] # Tên cột tiếng Việt (VD: "trạng thái")
            
            record = None
            context = {
                "noun": main_noun,
                "col_name": primary_col_name,
                "col_raw": col_raw,
                "role": role
            }

            if role == "IDENTITY":
                sql = self.sql_templates["IDENTITY"].format(table=table_name, col=col_raw)
                qs = self._generate_examples("IDENTITY", context)
                
                record = {
                    "document": f"{table_name} | Tra cứu theo {primary_col_name}", 
                    "description": f"Tìm kiếm chính xác {main_noun} dựa trên {primary_col_name}",
                    "sql": sql,
                    "examples": qs,
                    "keyword": f"{col_raw}, {primary_col_name}, tìm kiếm"
                }

            elif role == "DIMENSION":
                sql = self.sql_templates["DIMENSION"].format(table=table_name, col=col_raw)
                qs = self._generate_examples("DIMENSION", context)
                
                record = {
                    "document": f"{table_name} | Lọc theo {primary_col_name}",
                    "description": f"Liệt kê danh sách {main_noun} theo nhóm {primary_col_name}",
                    "sql": sql,
                    "examples": qs,
                    "keyword": f"{col_raw}, {primary_col_name}, danh sách"
                }

            elif role == "TEMPORAL":
                sql = self.sql_templates["TEMPORAL"].format(table=table_name, col=col_raw)
                qs = self._generate_examples("TEMPORAL", context)
                
                record = {
                    "document": f"{table_name} | Lọc theo thời gian ({primary_col_name})",
                    "description": f"Sao kê lịch sử {main_noun} trong khoảng thời gian",
                    "sql": sql,
                    "examples": qs,
                    "keyword": f"{col_raw}, thời gian, ngày tháng"
                }
            
            elif role == "METRIC":

                target_dim = cols_by_role["DIMENSION"][0] if cols_by_role["DIMENSION"] else None
                dim_col_raw = target_dim["name"] if target_dim else "status"
                dim_col_vn = self._get_synonyms(dim_col_raw, [])[0]

                sql = self.sql_templates["METRIC_SUM"].format(
                    table=table_name, col=col_raw, dim_col=dim_col_raw
                )
                
                metric_context = context.copy()
                metric_context["col_metric"] = primary_col_name 
                metric_context["col_group"] = dim_col_vn        
                metric_context["col_raw"] = dim_col_raw        
                
                qs = self._generate_examples("METRIC", metric_context)
                
                record = {
                    "document": f"{table_name} | Thống kê {primary_col_name} theo {dim_col_vn}",
                    "description": f"Tính tổng {primary_col_name} được phân loại bởi {dim_col_vn}",
                    "sql": sql,
                    "examples": qs,
                    "keyword": f"tổng {col_raw}, thống kê"
                }

            if record:
                dataset.append(record)

        # MULTI-COLUMN LOGIC: Kết hợp DIMENSION + TEMPORAL        
        if cols_by_role["DIMENSION"] and cols_by_role["TEMPORAL"]:

            dim_col = cols_by_role["DIMENSION"][0]
            time_col = cols_by_role["TEMPORAL"][0]
            
            dim_name_vn = self._get_synonyms(dim_col["name"], [])[0]
            
            sql_multi = self.sql_templates["MULTI_DIM_TIME"].format(
                table=table_name, 
                dim_col=dim_col["name"], 
                time_col=time_col["name"]
            )
            
            multi_context = {
                "noun": main_noun,
                "col_name": dim_name_vn,
                "col_raw": dim_col["name"], 
                "role": "DIMENSION"
            }
            
            qs_multi = self._generate_examples("MULTI_DIM_TIME", multi_context)
            
            dataset.append({
                "document": f"{table_name} | Lọc {dim_name_vn} theo Thời gian",
                "description": f"Kết hợp lọc theo {dim_name_vn} và khoảng ngày tháng",
                "sql": sql_multi,
                "examples": qs_multi,
                "keyword": f"{dim_col['name']}, {time_col['name']}, lọc đa điều kiện"
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
                "examples": "\n".join(item["examples"]), # Xuống dòng trong ô
                "keyword": item["keyword"],
                "metadata": json.dumps({"raw_text": item["sql"]}, ensure_ascii=False)
            })
        df = pd.DataFrame(rows)
        df.to_excel(output_path, index=False)
        print(f"💾 Kết quả lưu tại: {output_path}")