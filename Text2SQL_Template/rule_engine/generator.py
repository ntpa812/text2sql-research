import json
import pandas as pd
import itertools
import os
from pathlib import Path
from typing import List, Dict, Any

class RuleBasedGenerator:
    
    def __init__(self):

        self.vocab = {
            "verbs": {
                "lookup": ["Tra cứu", "Tìm", "Hiển thị", "Cho tôi xem", "Xem chi tiết", "Kiểm tra", "Liệt kê", "Search"],
                "agg": ["Tính tổng", "Tổng cộng", "Thống kê", "Cộng", "Xem tổng"],
                "filter": ["Lọc các", "Danh sách", "Những", "Các"],
            },
            "nouns": {
                "table": ["giao dịch", "lệnh chuyển tiền", "biến động số dư", "history"],
                "record": ["bản ghi", "thông tin", "dữ liệu"],
            },
            "connectors": ["có", "theo", "với", "của", "tại", "mang"],

            "col_mapping": {
                "amount": ["số tiền", "giá trị", "hạn mức"],
                "fee": ["phí", "tiền phí"],
                "status": ["trạng thái", "tình trạng", "kết quả"],
                "type": ["loại", "hình thức"],
                "channel": ["kênh", "nguồn"],
                "time": ["thời gian", "ngày", "giờ"],
                "user": ["người dùng", "khách hàng"],
                "bank": ["ngân hàng"],
                "id": ["mã", "số", "id"]
            }
        }

        self.sql_templates = {
            "IDENTITY": "SELECT * FROM {table} WHERE {col} = '{{{{{col}}}}}'",
            "DIMENSION": "SELECT * FROM {table} WHERE {col} = '{{{{{col}}}}}'",
            "METRIC_SUM": "SELECT SUM({col}) FROM {table} WHERE {dim_col} = '{{{{{dim_col}}}}}'",
            "TEMPORAL": "SELECT * FROM {table} WHERE {col} BETWEEN '{{{{start_date}}}}' AND '{{{{end_date}}}}' ORDER BY {col} DESC"
        }

    def _get_synonyms(self, col_name: str, suggested: List[str]) -> List[str]:
        """Lấy từ đồng nghĩa tiếng Việt cho tên cột"""
        synonyms = set(suggested)
        
        for key, vals in self.vocab["col_mapping"].items():
            if key in col_name.lower():
                synonyms.update(vals)
        
        if not synonyms:
            synonyms.add(col_name)
            
        return list(synonyms)

    def _generate_nlq(self, intent_type: str, col_synonyms: List[str], table_synonyms: List[str]) -> List[str]:
        """
        Thuật toán tổ hợp: Sinh ra tất cả các biến thể câu hỏi có thể.
        Công thức: [Verb] + [Noun Table] + [Connector] + [Col Name] + {Entity}
        """
        questions = []
        
        verbs = self.vocab["verbs"].get(intent_type, ["Tra cứu"])
        connectors = self.vocab["connectors"]
        
        combinations = itertools.product(verbs, table_synonyms, connectors, col_synonyms)
        
        for verb, table, conn, col in combinations:

            q1 = f"{verb} {table} {conn} {col} {{{{{{placeholder}}}}}}"
            questions.append(q1)
            
            if intent_type == "lookup":
                q2 = f"{col} {{{{{{placeholder}}}}}} là bao nhiêu"
                questions.append(q2)
                
        return list(set(questions))[:15]

    def generate_dataset(self, profile_path: str) -> List[Dict]:

        print(f"[*] Đang đọc profile từ: {profile_path}")
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f)
            
        table_name = Path(profile_path).stem
        columns = profile["columns"]
        
        dataset = []
        
        dimensions = [c for c in columns if c["role"] == "DIMENSION"]
        
        for col in columns:
            role = col["role"]
            col_name = col["name"]
            col_syns = self._get_synonyms(col_name, col["suggested_keywords"])
            table_syns = self.vocab["nouns"]["table"]

            record = None
            
            if role == "IDENTITY":
                sql = self.sql_templates["IDENTITY"].format(table=table_name, col=col_name)
                qs = self._generate_nlq("lookup", col_syns, table_syns)
                
                qs = [q.replace("{{placeholder}}", f"{{{{{col_name}}}}}") for q in qs]
                
                record = {
                    "document": f"Tra cứu {table_name} theo {col_name}",
                    "description": f"Tìm kiếm chính xác bản ghi dựa trên {col_name}",
                    "sql": sql,
                    "examples": qs,
                    "keyword": f"{col_name}, tra cứu, tìm kiếm"
                }

            elif role == "DIMENSION":
                sql = self.sql_templates["DIMENSION"].format(table=table_name, col=col_name)
                qs = self._generate_nlq("filter", col_syns, table_syns)
                qs = [q.replace("{{placeholder}}", f"{{{{{col_name}}}}}") for q in qs]
                
                record = {
                    "document": f"Lọc {table_name} theo {col_name}",
                    "description": f"Liệt kê danh sách theo tiêu chí {col_name}",
                    "sql": sql,
                    "examples": qs,
                    "keyword": f"{col_name}, danh sách, lọc"
                }

            elif role == "METRIC":
                
                # Mặc định ghép với Dimension đầu tiên (ví dụ: trans_status)
                dim_target = dimensions[0]["name"] if dimensions else "trans_status"
                
                sql = self.sql_templates["METRIC_SUM"].format(
                    table=table_name, col=col_name, dim_col=dim_target
                )
                
                qs = []
                for v in self.vocab["verbs"]["agg"]:
                    for s in col_syns:
                        qs.append(f"{v} {s} của các giao dịch có {dim_target} là {{{{{dim_target}}}}}")
                        qs.append(f"Xem tổng {s} theo {dim_target} {{{{{dim_target}}}}}")

                record = {
                    "document": f"Thống kê tổng {col_name} theo {dim_target}",
                    "description": f"Tính tổng giá trị {col_name} được gom nhóm bởi {dim_target}",
                    "sql": sql,
                    "examples": qs,
                    "keyword": f"tổng {col_name}, thống kê"
                }

            elif role == "TEMPORAL":
                sql = self.sql_templates["TEMPORAL"].format(table=table_name, col=col_name)
                
                qs = [
                    f"Sao kê giao dịch từ ngày {{{{start_date}}}} đến {{{{end_date}}}}",
                    f"Liệt kê lịch sử trong khoảng thời gian {{{{start_date}}}} - {{{{end_date}}}}",
                    f"Kiểm tra giao dịch phát sinh từ {{{{start_date}}}} tới {{{{end_date}}}}",
                    f"Cho tôi xem biến động số dư giữa {{{{start_date}}}} và {{{{end_date}}}}"
                ]
                
                record = {
                    "document": f"Tra cứu {table_name} theo khoảng thời gian ({col_name})",
                    "description": f"Lọc dữ liệu phát sinh trong một khoảng ngày giờ",
                    "sql": sql,
                    "examples": qs,
                    "keyword": "thời gian, ngày tháng, sao kê"
                }

            if record:
                dataset.append(record)

        print(f"Đã sinh {len(dataset)} logic SQL dựa trên luật.")
        return dataset

    def export_excel(self, dataset: List[Dict], output_path: str):

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        
        rows = []
        for item in dataset:
            rows.append({
                "document": item["document"],
                "description": item["description"],
                "examples": "|".join(item["examples"]), 
                "keyword": item["keyword"],
                "metadata": json.dumps({"raw_text": item["sql"]}, ensure_ascii=False)
            })
            
        df = pd.DataFrame(rows)
        df.to_excel(output_path, index=False)
        print(f"💾 Kết quả lưu tại: {output_path}")

if __name__ == "__main__":

    BASE_DIR = Path(__file__).resolve().parent
    
    INPUT_PROFILE = BASE_DIR / "profiles" / "semantic_profile_transaction.json"
    
    OUTPUT_EXCEL = BASE_DIR / "output" / "ddq_final_rule_based.xlsx"
    
    if not INPUT_PROFILE.exists():
        print(f"❌ Không tìm thấy {INPUT_PROFILE}. Hãy chạy run_profiler.py trước!")
    else:
        gen = RuleBasedGenerator()
        data = gen.generate_dataset(str(INPUT_PROFILE))
        gen.export_excel(data, str(OUTPUT_EXCEL))