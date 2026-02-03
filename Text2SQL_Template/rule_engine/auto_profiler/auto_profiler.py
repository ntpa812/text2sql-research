import pandas as pd
import numpy as np
import sys
import re
from pathlib import Path
from typing import Dict, List

# Setup path để import configs
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

try:
    from configs.dictionary import COMMON_DICTIONARY
except ImportError:
    COMMON_DICTIONARY = {}

# Import AI (Có xử lý ngoại lệ nếu chưa cài xong)
try:
    from sentence_transformers import SentenceTransformer, util
    import torch
    HAS_AI = True
except ImportError:
    HAS_AI = False
    print("⚠️ Cảnh báo: Chưa cài sentence-transformers. Chạy chế độ Dictionary-only.")

class AutoProfiler:
    def __init__(self):
        # 1. Load Từ điển (Cốt lõi cho từ viết tắt)
        self.vocab = COMMON_DICTIONARY
        self.glossary = {}
        self._build_glossary()
        
        # 2. Load AI (Phụ trợ cho từ lạ)
        self.model = None
        if HAS_AI:
            print("[*] Đang tải AI Model (Hybrid Mode)...")
            try:
                # Dùng model nhỏ, nhanh, hiểu đa ngôn ngữ
                self.model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
                
                # Kho khái niệm chuẩn (Target Concepts)
                self.concepts = [
                    "số tiền", "mã giao dịch", "ngày giao dịch", "trạng thái",
                    "số tài khoản", "khách hàng", "kênh", "nội dung",
                    "phí", "người thụ hưởng", "ngân hàng", "lãi suất"
                ]
                self.concept_embeddings = self.model.encode(self.concepts, convert_to_tensor=True)
                print("[*] AI Model đã sẵn sàng!")
            except Exception as e:
                print(f"❌ Lỗi load AI: {e}. Chuyển sang chế độ Dictionary-only.")
                HAS_AI = False

    def _build_glossary(self):
        """Xây dựng từ điển phẳng để tra cứu nhanh"""
        # Load từ Configs
        for k, v in self.vocab.get("col_mapping", {}).items():
            self.glossary[k] = v[0]
        for k, v in self.vocab.get("tables", {}).items():
            self.glossary[k] = v[0]
        for k, v in self.vocab.get("suffixes", {}).items():
            clean_k = k.replace("_", "")
            self.glossary[clean_k] = v[0]
            
        # Các từ viết tắt ngành Bank (Hard-code bổ trợ)
        extras = {
            "amt": "số tiền", "val": "giá trị", "bal": "số dư",
            "dt": "ngày", "tm": "giờ", "cd": "mã",
            "no": "số", "id": "mã", "desc": "nội dung",
            "src": "nguồn", "dst": "đích", "acc": "tài khoản",
            "cif": "khách hàng", "cust": "khách hàng",
            "trans": "giao dịch", "chk": "kiểm tra",
            "ccy": "loại tiền"
        }
        self.glossary.update(extras)

    def _ai_guess(self, text: str) -> str:
        """Dùng AI đoán nghĩa nếu từ điển bó tay"""
        if not HAS_AI or not self.model: return text
        
        # Encode từ cần đoán
        embedding = self.model.encode(text, convert_to_tensor=True)
        # So khớp với kho khái niệm
        scores = util.cos_sim(embedding, self.concept_embeddings)[0]
        best_idx = torch.argmax(scores).item()
        score = scores[best_idx].item()
        
        # Chỉ tin AI nếu độ tự tin > 0.45
        if score > 0.45:
            return self.concepts[best_idx]
        return text

    def _translate_col_name(self, col_name: str) -> str:
        """Hàm dịch thuật toán Hybrid (Dictionary First -> AI Second)"""
        # 1. Tách từ: cust_trans_amt -> [cust, trans, amt]
        parts = col_name.lower().split('_')
        translated_parts = []
        
        for p in parts:
            # Ưu tiên 1: Tra từ điển (Chính xác tuyệt đối với từ viết tắt)
            if p in self.glossary:
                translated_parts.append(self.glossary[p])
            else:
                # Ưu tiên 2: Nếu từ điển không có, hỏi AI
                # VD: từ 'billing' có thể không có trong dict, AI sẽ đoán là 'thanh toán'
                guessed = self._ai_guess(p)
                translated_parts.append(guessed)

        # 2. Xử lý ngữ pháp (Đảo từ)
        # Tiếng Anh: Customer Name -> Tiếng Việt: Tên Khách hàng
        raw_vn = " ".join(translated_parts)
        words = raw_vn.split()
        
        if len(words) > 1:
            prefixes = ["mã", "tên", "ngày", "số", "loại", "trạng thái"]
            # Nếu từ cuối cùng là từ chỉ loại (VD: Name, Id), đảo lên đầu
            if words[-1] in prefixes:
                last = words.pop()
                words.insert(0, last)
                
        return " ".join(words)

    def _detect_role(self, series: pd.Series, col_name: str) -> str:
        """Đoán Role cột"""
        col_lower = col_name.lower()
        if any(x in col_lower for x in ["id", "code", "no", "key"]): return "IDENTITY"
        if any(x in col_lower for x in ["date", "time", "dt", "tm"]): return "TEMPORAL"
        if any(x in col_lower for x in ["amt", "amount", "price", "fee", "val"]): return "METRIC"
        
        try:
            if np.issubdtype(series.dtype, np.number):
                if series.nunique() / len(series) > 0.9: return "IDENTITY"
                return "METRIC"
            else:
                if series.nunique() < 20: return "DIMENSION"
                return "ATTRIBUTE"
        except:
            return "ATTRIBUTE"

    def analyze(self, file_path: str) -> Dict:
        """Hàm chính gọi bởi test.py hoặc main app"""
        try:
            if str(file_path).endswith(".csv"):
                df = pd.read_csv(file_path, nrows=1000)
            else:
                df = pd.read_excel(file_path, nrows=1000)
        except Exception as e:
            print(f"❌ Lỗi đọc file: {e}")
            return {}

        table_name = Path(file_path).stem
        profile = {"table_name": table_name, "columns": []}

        for col in df.columns:
            # 1. Đoán Role
            role = self._detect_role(df[col], col)
            
            # 2. Dịch tên (Dùng Hybrid Logic)
            vn_name = self._translate_col_name(col)
            
            # 3. Tạo Keyword
            keywords = [vn_name]
            if role == "IDENTITY" and "mã" in vn_name:
                keywords.append(vn_name.replace("mã", "số"))
            if role == "METRIC" and "số tiền" in vn_name:
                keywords.append(vn_name.replace("số tiền", "giá trị"))

            profile["columns"].append({
                "name": col,
                "role": role,
                "suggested_keywords": keywords
            })

        return profile