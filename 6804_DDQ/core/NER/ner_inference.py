"""
NER Inference Module - Service-ready
Model được load sẵn ngay khi import, sẵn sàng phục vụ request
"""

import json
import re
import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer
from typing import Optional, List, Dict
from core.NER.vietnamese_time_parser import VietnameseTimeParser
# from tatools01.ParamsBase import TactParameters
from config import mPs_ner
# AppName = 'My_Project_Name'


# class Params_ner(TactParameters):
#     def __init__(self):
#         super().__init__(ModuleName="ner_inference", params_dir='./')
#         self.HD = ["Chương trình NER"]
#         self.ner_model_path = "/home/javis-ai/Javis_AI_UAT/api/weights/Ner/NER New Model - 14 entities"
#         self.load_then_save_to_yaml(file_path=f"{AppName}.yml")


# mPs_ner = Params_ner()
print = mPs_ner.mlog


class NERInference:
    """
    NER Inference Engine - Singleton (Eager Loading)
    Model được load ngay khi khởi tạo, không dùng thread.

    Usage:
        from ner_inference import ner_engine, ner_predict

        # Cách 1: Sử dụng instance đã load sẵn
        results = ner_engine.predict("text here")

        # Cách 2: Sử dụng hàm tiện ích
        results = ner_predict("text here")
    """

    def __init__(self, model_path: Optional[str] = None, device: Optional[torch.device] = None):
        self._model_path = model_path or mPs_ner.ner_model_path
        self._device = device or torch.device("cuda" if torch.cuda.is_available() else "cpu")

        print(f"[NER] Loading model from {self._model_path}...")

        # Load model và tokenizer
        self._load_model()

        # Compile regex patterns một lần
        self._compile_patterns()
        
        # Initialize VietnameseTimeParser
        self._time_parser = VietnameseTimeParser()

        print(f"[NER] Model loaded successfully on {self._device}")

    def _load_model(self) -> None:
        """Load model, tokenizer và label map"""
        self._model = AutoModelForTokenClassification.from_pretrained(self._model_path)
        self._tokenizer = AutoTokenizer.from_pretrained(self._model_path)

        with open(f"{self._model_path}/label_map.json", "r", encoding="utf-8") as f:
            self._id_to_label: Dict[int, str] = {v: k for k, v in json.load(f).items()}

        self._model.to(self._device).eval()

        # Tối ưu: disable gradient computation permanently
        for param in self._model.parameters():
            param.requires_grad = False

    def _compile_patterns(self) -> None:
        """Pre-compile tất cả regex patterns"""
        self._whitespace_pattern = re.compile(r'\s+')
        self._time_pattern = re.compile(r'(\d+)\s*:\s*(\d+)')
        self._decimal_pattern = re.compile(r'(\d+)\s*\.\s*(\d+)')
        self._comma_pattern = re.compile(r'(\d+)\s*,\s*(\d+)')
        self._digit_pattern = re.compile(r'\d+')
        self._digit_search = re.compile(r'\d')
        self._punct_pattern = re.compile(r'^[.,;!?:"\'()[\]{}«»`~*—–\-\s]+|[.,;!?:"\'()[\]{}«»`~*—–\-\s]+$')
        self._special_only = re.compile(r'[^\w\s]+')
        self._paren_pattern = re.compile(r'[()]')

    def _postprocess_entity(self, entity_tokens: List[str], entity_type: str) -> str:
        """Xử lý hậu kỳ entity text"""
        text = " ".join(entity_tokens).replace("_", " ")
        text = self._whitespace_pattern.sub(' ', text).strip()

        text = self._time_pattern.sub(r'\1:\2', text)
        text = self._decimal_pattern.sub(r'\1.\2', text)
        text = self._comma_pattern.sub(r'\1,\2', text)

        if entity_type == "Số_tài_khoản":
            nums = self._digit_pattern.findall(text)
            text = ''.join(nums) if nums else ""
            if not text:
                return ""  # Bỏ qua entity này nếu không có số
        elif entity_type == "giờ_giao_dịch":
            m = self._digit_search.search(text)
            text = text[m.start():].strip() if m else text
        elif entity_type == "bank":
            # Remove common prefixes
            text = re.sub(r'^(ngân hàng|nh|ngân|hàng)\b', '', text, flags=re.IGNORECASE).strip()
            if not text:
                return ""
        elif entity_type == "kênh_giao_dịch":
            # Remove "kênh" from the entity
            text = re.sub(r'\bkênh\b', '', text, flags=re.IGNORECASE).strip()
            if not text:
                return ""

        text = self._punct_pattern.sub('', text)

        return "" if self._special_only.fullmatch(text) else text

    def predict(self, text: str, max_len: int = 200) -> List[Dict[str, str]]:
        """
        Nhận diện entities trong text

        Args:
            text: Văn bản cần nhận diện
            max_len: Độ dài tối đa của sequence

        Returns:
            List các dict {entity_type: entity_value}
        """
        # Tiền xử lý
        text = self._paren_pattern.sub('', text)
        words = text.split()

        if not words:
            return []

        # Tokenize
        encoded = self._tokenizer(
            words,
            is_split_into_words=True,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_len
        )
        word_ids = encoded.word_ids()
        inputs = {k: v.to(self._device) for k, v in encoded.items()}

        # Inference
        with torch.inference_mode():
            logits = self._model(**inputs).logits
            preds = torch.argmax(logits, dim=2).cpu().numpy()[0]

        # Extract entities
        entities: List[tuple] = []
        cur_type: Optional[str] = None
        cur_tokens: List[str] = []
        prev_idx: Optional[int] = None

        for idx, word_idx in enumerate(word_ids):
            if word_idx is not None and word_idx != prev_idx:
                label = self._id_to_label.get(preds[idx], "O")

                if label.startswith("B-"):
                    if cur_type:
                        entities.append((cur_type, cur_tokens[:]))
                    cur_type = label[2:]
                    cur_tokens = [words[word_idx]]
                elif label.startswith("I-"):
                    entity_type = label[2:]
                    if cur_type is None:
                        cur_type = entity_type
                        cur_tokens = [words[word_idx]]
                    elif cur_type == entity_type:
                        cur_tokens.append(words[word_idx])
                    else:
                        entities.append((cur_type, cur_tokens[:]))
                        cur_type = entity_type
                        cur_tokens = [words[word_idx]]
                else:
                    if cur_type:
                        entities.append((cur_type, cur_tokens[:]))
                        cur_type, cur_tokens = None, []

                prev_idx = word_idx

        if cur_type:
            entities.append((cur_type, cur_tokens))

        # Postprocess
        result: List[Dict[str, str]] = []
        for etype, tokens in entities:
            if tokens:
                processed_value = self._postprocess_entity(tokens, etype)
                if processed_value:
                    # Xử lý entity Ngày_giao_dịch bằng VietnameseTimeParser
                    if etype == "Ngày_giao_dịch":
                        from_date, to_date = self._time_parser.parse(processed_value)
                        if from_date and to_date:
                            result.append({"from_date": from_date})
                            result.append({"to_date": to_date})
                        else:
                            # Nếu parse thất bại, vẫn giữ nguyên entity
                            result.append({etype: processed_value})
                    else:
                        result.append({etype: processed_value})

        return result

    def print_iob_tags(self, text: str, max_len: int = 200) -> None:
        """In ra IOB tags cho mỗi từ trong text"""
        words = self._paren_pattern.sub('', text).split()

        if not words:
            return

        encoded = self._tokenizer(
            words,
            is_split_into_words=True,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=max_len
        )
        word_ids = encoded.word_ids()
        inputs = {k: v.to(self._device) for k, v in encoded.items()}

        with torch.inference_mode():
            preds = torch.argmax(self._model(**inputs).logits, dim=2).cpu().numpy()[0]

        prev_idx = None
        for idx, word_idx in enumerate(word_ids):
            if word_idx is not None and word_idx != prev_idx:
                label = self._id_to_label.get(preds[idx], "O")
                print(f"{words[word_idx]:<20} {label}")
                prev_idx = word_idx

    @property
    def device(self) -> torch.device:
        """Trả về device đang sử dụng"""
        return self._device

    @property
    def model_path(self) -> str:
        """Trả về đường dẫn model"""
        return self._model_path


# ============================================================
# EAGER LOADING: Model được load ngay khi import module
# ============================================================

print("[NER] Initializing NER Service...")
ner_engine = NERInference()
print("[NER] NER Service ready!")


# ============================================================
# Hàm tiện ích để gọi nhanh từ bên ngoài
# ============================================================

def ner_predict(query: str, max_len: int = 200) -> List[Dict[str, str]]:
    """
    Hàm tiện ích để predict NER entities

    Args:
        query: Văn bản cần nhận diện
        max_len: Độ dài tối đa

    Returns:
        List các dict {entity_type: entity_value}

    Example:
        >>> from ner_inference import ner_predict
        >>> results = ner_predict("Cho tôi xem các giao dịch năm ngoái của tk vp 123123123")
        >>> print(results)
        [{'from_date': '2024-01-01'}, {'to_date': '2024-12-31'}, {'Số_tài_khoản': '123123123'}]
    """
    print(f"\n[NER] Câu gốc: {query}")
    result = ner_engine.predict(query, max_len)
    print(f"[NER] Entities: {result}")
    return result


def ner_predict_raw(query: str, max_len: int = 200) -> List[Dict[str, str]]:
    """
    Predict NER entities (không log)

    Args:
        query: Văn bản cần nhận diện
        max_len: Độ dài tối đa

    Returns:
        List các dict {entity_type: entity_value}
    """
    return ner_engine.predict(query, max_len)


# ============================================================
# Main cho testing
# ============================================================

if __name__ == "__main__":
    # Test với câu có ngày giao dịch
    test_query = 'Cho tôi xem các giao dịch năm ngoái của tk vp 123123123'

    # Cách 1: Sử dụng hàm tiện ích
    print("\n" + "="*60)
    print("Test 1: Sử dụng hàm ner_predict")
    print("="*60)
    results = ner_predict(test_query)

    # Cách 2: Sử dụng instance trực tiếp (đã load sẵn)
    print("\n" + "="*60)
    print("Test 2: Sử dụng ner_engine trực tiếp")
    print("="*60)
    print(f"Câu gốc: {test_query}\n")
    
    print("IOB Tags:")
    ner_engine.print_iob_tags(test_query)
    
    print("\nEntities:")
    results2 = ner_engine.predict(test_query)
    for entity_dict in results2:
        for entity_type, value in entity_dict.items():
            print(f"{entity_type:<30} {value}")

    # Test thêm với các câu khác
    test_cases = [
        'Giao dịch từ đầu tháng đến cuối tháng của tk 456789',
        'Xem lịch sử 3 ngày trước tài khoản Vietcombank',
        'Các giao dịch quý 1 năm nay'
    ]
    
    print("\n" + "="*60)
    print("Additional Test Cases:")
    print("="*60)
    
    for test_text in test_cases:
        print(f"\nCâu: {test_text}")
        print("Entities:")
        for entity_dict in ner_engine.predict(test_text):
            for entity_type, value in entity_dict.items():
                print(f"  {entity_type:<30} {value}")
