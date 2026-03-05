import json
import random
from typing import List, Dict
from pathlib import Path
import pandas as pd

from configs.dictionary import COMMON_DICTIONARY
from .faker_utils import DataFaker
from .grammar_templates import GrammarLibrary

try:
    from .dl_utils import LocalParaphraser
except ImportError:
    LocalParaphraser = None
    
class RuleBasedGenerator:
    def __init__(self, vocab=None, ai_model=None):
        self.faker = DataFaker()
        self.grammar = GrammarLibrary()
        self.NUM_EXAMPLES = 10
        self.ai_model = ai_model
        self.paraphraser = None
        
        if self.ai_model and LocalParaphraser:
            model_path = ai_model if isinstance(ai_model, str) else "models/my_banking_ai"
            self.paraphraser = LocalParaphraser(model_path=model_path)
        
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
            "MIX_TYPE_AMOUNT": "SELECT * FROM {table} WHERE {type_col} = '{{{{{type_col}}}}}' AND {amt_col} > {{{{{amt_col}}}}} AND {status_col} = 'SUCCESS'",
            "COMPARISON_GT": "SELECT * FROM {table} WHERE {col} > {val}",
            "COMPARISON_LT": "SELECT * FROM {table} WHERE {col} < {val}",
            "RANKING_TOP": "SELECT * FROM {table} ORDER BY {col} DESC LIMIT {k}",
            "RANKING_BOTTOM": "SELECT * FROM {table} ORDER BY {col} ASC LIMIT {k}",
            "GROUP_BY_SUM": "SELECT {dim_col}, SUM({metric_col}) FROM {table} GROUP BY {dim_col}",
            "WHERE_AND_GT": "SELECT * FROM {table} WHERE {dim_col} = '{{{{{dim_col}}}}}' AND {met_col} > {{{{{met_col}}}}}",
            "WHERE_AND_LT": "SELECT * FROM {table} WHERE {dim_col} = '{{{{{dim_col}}}}}' AND {met_col} < {{{{{met_col}}}}}"
        }

    def _get_table_synonyms(self, table_name):
        return self.vocab.get("tables", {}).get(table_name, [table_name])

    def _classify_column(self, col_name):
        col_name = col_name.lower()
        if any(x in col_name for x in ["id", "key", "guid", "uuid"]) and "customer" not in col_name and "trans" not in col_name:
            return "TECH_ID"
        return "BUSINESS_ID"

    def _get_column_synonyms(self, col_name: str, suggested: List[str] = None) -> List[str]:
        specific_cols = self.vocab.get("specific_columns", {})
        dict_synonyms = specific_cols.get(col_name, [])
        suggested_synonyms = suggested if suggested else []
        final_synonyms = set(dict_synonyms)
        final_synonyms.update(suggested_synonyms)
        final_synonyms.add(col_name)
        return list(final_synonyms)
    
    def _get_canonical_name(self, col_name: str, suggested: List[str] = None) -> str:
        specific_cols = self.vocab.get("specific_columns", {})
        if col_name in specific_cols and specific_cols[col_name]:
            return specific_cols[col_name][0] 
            
        clean_col = col_name.split('_')[-1] 
        mapping = self.vocab.get("col_mapping", {})
        
        if col_name in mapping: 
            return mapping[col_name][0]
        if clean_col in mapping:
            return mapping[clean_col][0]

        return col_name

    def _get_safe_display_name(self, synonyms: List[str], default_name: str) -> str:
        if not synonyms:
            return default_name
        valid_syns = [s for s in synonyms if len(s) > 1]
        if not valid_syns:
            return default_name
        return min(valid_syns, key=len)
    
    def _finalize_examples(self, examples: List[str]) -> List[str]:
        unique_ex = sorted(list(set(examples))) 
        if len(unique_ex) > self.NUM_EXAMPLES:
            return random.sample(unique_ex, self.NUM_EXAMPLES)
        return unique_ex
    
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
        if val_ref and isinstance(val_ref, str) and val_ref in vocab_values:
            target_group = vocab_values[val_ref]
        elif val_ref and isinstance(val_ref, dict):
            target_group = val_ref

        if target_group and group_type == "DIMENSION":
            keys = list(target_group.keys())
            if keys:
                k = random.choice(keys)
                adj_list = target_group[k]
                if adj_list:
                    adj = random.choice(adj_list) if isinstance(adj_list, list) else str(adj_list)
                    noun = context.get('noun', '')
                    v = random.choice(all_action_verbs)
                    
                    generated_qs.add(f"{noun} {adj}")
                    generated_qs.add(f"{v} các {noun} {adj}")
                    generated_qs.add(f"{v} danh sách {noun} là {adj}")

        for tmpl in templates:
            if group_type == "DIMENSION":
                chosen_verb = random.choice(all_action_verbs)
            elif group_type == "IDENTITY": 
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

    def _generate_complex_queries(self, table_name: str, columns: List[Dict]) -> List[Dict]:
        complex_dataset = []
        metrics = [c for c in columns if c['role'] == 'METRIC']
        dimensions = [c for c in columns if c['role'] in ['DIMENSION', 'ATTRIBUTE']]
        
        if not metrics: return []

        for col in metrics:
            col_name = col['name']
            canonical_name = self._get_canonical_name(col_name)
            synonyms = self._get_column_synonyms(col_name, col.get('suggested_keywords', []))

            keyword_str = ", ".join(synonyms)
            
            all_examples = []
            for _ in range(5): 
                fake_val = self.faker._generate_amount() 
                for syn in synonyms:
                    qs_gt = self.grammar.get_templates("COMPARISON")
                    exs = [
                        self.grammar.format_template(t, verb="Tìm", noun=table_name, col_metric=syn, val=fake_val)
                        for t in qs_gt if "lớn hơn" in t or "trên" in t
                    ]
                    all_examples.extend(exs)

            final_examples = self._finalize_examples(all_examples)
            if final_examples:
                complex_dataset.append({
                    "document": f"{table_name} | So sánh lớn hơn {canonical_name}",
                    "description": f"Tìm kiếm {table_name} có {canonical_name} > giá trị",
                    "sql": self.sql_templates["COMPARISON_GT"].format(table=table_name, col=col_name, val="{{val}}"),
                    "examples": final_examples,
                    "keyword": keyword_str + ", so sánh"
                })

        for col in metrics:
            col_name = col['name']
            canonical_name = self._get_canonical_name(col_name, col.get('suggested_keywords', []))
            synonyms = self._get_column_synonyms(col_name, col.get('suggested_keywords', []))
            
            all_examples = []
            for _ in range(5):
                k = random.choice([5, 10, 20])
                for syn in synonyms:
                    qs_rank = self.grammar.get_templates("RANKING")
                    exs = [
                        self.grammar.format_template(t, k=k, noun=table_name, col_metric=syn)
                        for t in qs_rank if "nhất" in t
                    ]
                    all_examples.extend(exs)
            
            final_examples = self._finalize_examples(all_examples)
            if final_examples:
                complex_dataset.append({
                    "document": f"{table_name} | Xếp hạng Top {canonical_name}",
                    "description": f"Lấy danh sách bản ghi có {canonical_name} cao nhất",
                    "sql": self.sql_templates["RANKING_TOP"].format(table=table_name, col=col_name, k="{{k}}"),
                    "examples": final_examples,
                    "keyword": "xếp hạng"
                })

        if dimensions and metrics:
            for dim in dimensions:
                for met in metrics:
                    dim_name = dim['name']
                    met_name = met['name']
                    
                    dim_canonical = self._get_canonical_name(dim_name)
                    met_canonical = self._get_canonical_name(met_name)
                    dim_syns = self._get_column_synonyms(dim_name, dim.get('suggested_keywords', []))
                    met_syns = self._get_column_synonyms(met_name, met.get('suggested_keywords', []))
                    combined_keywords = ", ".join(dim_syns + met_syns)
                    d_syn_safe = self._get_safe_display_name(dim_syns, dim_canonical)
                    m_syn_safe = self._get_safe_display_name(met_syns, met_canonical)

                    all_examples = []

                    for _ in range(4): 

                        dim_val = "UNKNOWN"
                        dim_val_display = "UNKNOWN"
                        val_ref = dim.get('value_ref')
                        if val_ref and isinstance(val_ref, str):
                            val_ref = self.vocab.get("values", {}).get(val_ref)
                        if val_ref and isinstance(val_ref, dict):
                            try:
                                possible_codes = list(val_ref.keys())
                                if possible_codes:
                                    dim_val = random.choice(possible_codes)
                                    raw = val_ref[dim_val]
                                    dim_val_display = random.choice(raw) if isinstance(raw, list) else str(raw)
                                else:
                                    dim_val = self.faker.get_fake_value(dim_name, "DIMENSION")
                                    dim_val_display = dim_val
                            except:
                                dim_val = self.faker.get_fake_value(dim_name, "DIMENSION")
                                dim_val_display = dim_val
                        else:
                            dim_val = self.faker.get_fake_value(dim_name, "DIMENSION")
                            dim_val_display = dim_val

                        met_val = self.faker._generate_amount()
                        
                        qs_and_gt = self.grammar.get_templates("FILTER_AND_GT")
                        exs = [
                            self.grammar.format_template(t, 
                                noun=table_name, 
                                dim_col=d_syn_safe, dim_val=dim_val_display,
                                met_col=m_syn_safe, met_val=met_val
                            ) for t in qs_and_gt
                        ]
                        all_examples.extend(exs)

                    final_examples = self._finalize_examples(all_examples)
                    if final_examples:
                        complex_dataset.append({
                            "document": f"{table_name} | Lọc {dim_canonical} và {met_canonical}",
                            "description": f"Tìm bản ghi theo {dim_canonical} và {met_canonical}",
                            "sql": self.sql_templates.get("WHERE_AND_GT", "").format(
                                table=table_name, 
                                dim_col=dim_name, 
                                met_col=met_name, 
                            ),
                            "examples": final_examples,
                            "keyword": combined_keywords + f"{dim_canonical} và {met_canonical}"
                        })

        return complex_dataset

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
        
        OVERSAMPLING_FACTOR = 3

        for col in columns:
            role = col["role"]
            col_raw = col["name"]
            
            if col_raw in seen_keys: continue
            seen_keys.add(col_raw)
            
            canonical_name = self._get_canonical_name(col_raw)
            synonyms = self._get_column_synonyms(col_raw, col.get('suggested_keywords', []))
            keyword_str = ", ".join(synonyms)
            
            all_examples = []
            
            for _ in range(OVERSAMPLING_FACTOR):
                val = self.faker.get_fake_value(col_raw, role)
                
                for syn in synonyms:
                    if role == "IDENTITY" and self._classify_column(col_raw) == "TECH_ID": 
                        continue

                    context = {
                        "noun": main_noun, 
                        "col_name": syn,
                        "col_raw": col_raw, 
                        "role": role,
                        "val": val,
                        "value_ref": col.get("value_ref")
                    }

                    if role == "IDENTITY":
                        qs = self._generate_natural_queries("IDENTITY", context)
                        all_examples.extend(qs)
                    elif role == "DIMENSION":
                        qs = self._generate_natural_queries("DIMENSION", context)
                        all_examples.extend(qs)
                    elif role == "METRIC":
                        qs = [
                            f"Tổng {syn} là bao nhiêu?",
                            f"Tính tổng {syn}",
                            f"Thống kê {syn} hôm nay",
                            f"Cho tôi xem tổng {syn}"
                        ]
                        all_examples.extend(qs)
                    elif role == "TEMPORAL":
                        start_d = self.faker._generate_date(range_days=60)
                        end_d = self.faker._generate_date(range_days=0)
                        qs = [
                            f"Sao kê {main_noun} theo {syn} từ ngày {start_d} đến ngày {end_d}",
                            f"Lọc {main_noun} có {syn} trong khoảng {start_d} - {end_d}",
                            f"Xem lịch sử {main_noun} dựa trên {syn} từ {start_d} tới {end_d}"
                        ]
                        all_examples.extend(qs)

            final_examples = self._finalize_examples(all_examples)

            if final_examples:
                doc_title = ""
                description = ""
                sql = ""
                
                if role == "IDENTITY":
                    doc_title = f"{table_name} | Tra cứu {canonical_name}"
                    description = f"Tra cứu chính xác theo {canonical_name} ({col.get('description', '')})"
                    sql = self.sql_templates["IDENTITY"].format(table=table_name, col=col_raw)
                elif role == "DIMENSION":
                    doc_title = f"{table_name} | Lọc {canonical_name}"
                    description = f"Lọc dữ liệu theo {canonical_name}"
                    status_clause = ""
                    if spec_cols["status"] and col_raw != spec_cols["status"]["name"] and "status" not in col_raw.lower():
                        status_clause = f" AND {spec_cols['status']['name']} = 'SUCCESS'"
                    sql = self.sql_templates["DIMENSION"].format(table=table_name, col=col_raw) + status_clause
                elif role == "METRIC":
                    doc_title = f"{table_name} | Thống kê {canonical_name}"
                    description = f"Tính tổng giá trị {canonical_name}"
                    sql = f"SELECT SUM({col_raw}) FROM {table_name}"
                    if spec_cols["status"]: sql += f" WHERE {spec_cols['status']['name']} = 'SUCCESS'"
                elif role == "TEMPORAL":
                    doc_title = f"{table_name} | Lọc thời gian theo {canonical_name}"
                    description = f"Truy vấn lịch sử dựa trên cột {canonical_name}"
                    sql = self.sql_templates["TEMPORAL"].format(table=table_name, col=col_raw)

                if doc_title:
                    dataset.append({
                        "document": doc_title,
                        "description": description,
                        "sql": sql,
                        "examples": final_examples, 
                        "keyword": keyword_str
                    })

        complex_data = self._generate_complex_queries(table_name, columns)
        dataset.extend(complex_data)

        if spec_cols["type"] and spec_cols["amount"] and spec_cols["status"]:
            type_c = spec_cols["type"]["name"]
            amt_c = spec_cols["amount"]["name"]
            stt_c = spec_cols["status"]["name"]
            sql_mix = self.sql_templates["MIX_TYPE_AMOUNT"].format(table=table_name, type_col=type_c, amt_col=amt_c, status_col=stt_c)
            
            qs_mix = []
            for _ in range(5): 
                type_vals = self.faker.dict_type
                if type_vals:
                    key = random.choice(list(type_vals.keys()))
                    vals = type_vals[key]
                    adj = random.choice(vals) if isinstance(vals, list) else str(vals)
                    amt = self.faker._generate_amount()
                    qs_mix.append(f"{main_noun} {adj} trên {amt}")
                    qs_mix.append(f"Tìm các {main_noun} {adj} > {amt}")
                    qs_mix.append(f"Liệt kê giao dịch {adj} có giá trị lớn hơn {amt}")
            
            final_mix = self._finalize_examples(qs_mix)
            if final_mix:
                dataset.append({
                    "document": f"{table_name} | Lọc Loại theo số tiền",
                    "description": "Lọc nâng cao: Loại giao dịch theo số tiền tối thiểu",
                    "sql": sql_mix,
                    "examples": final_mix,
                    "keyword": "loại giao dịch theo số tiền"
                })

        if self.ai_model and self.paraphraser and self.paraphraser.is_ready:
            print(f"> Đang dùng AI ({self.paraphraser.device}) để chau chuốt lại {len(dataset)} nhóm câu hỏi...")
            
            for idx, item in enumerate(dataset):
                original_examples = item.get("examples", [])
                if not original_examples: continue
                
                seed_samples = original_examples[:2]
                ai_generated = []
                
                for seed in seed_samples:
                    try:
                        variants = self.paraphraser.paraphrase(seed, num_return=2)
                        ai_generated.extend(variants)
                    except Exception:
                        continue
                
                combined = list(set(original_examples + ai_generated))
                
                if len(combined) > self.NUM_EXAMPLES:
                    item["examples"] = random.sample(combined, self.NUM_EXAMPLES)
                else:
                    item["examples"] = combined
                
                if idx > 0 and idx % 5 == 0:
                    print(f"  - Đã xử lý xong {idx}/{len(dataset)} intents")
        
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