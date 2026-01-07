"""
NER Inference Module - Service-ready
Model được load sẵn ngay khi import, sẵn sàng phục vụ request
"""

import json
import re
import torch
from transformers import AutoModelForTokenClassification, AutoTokenizer
from typing import Optional, List, Tuple, Dict
from config import mPs_ner
# from tatools01.ParamsBase import TactParameters

# AppName = 'My_Project_Name'


# class Params_ner(TactParameters):
#     def __init__(self):
#         super().__init__(ModuleName="ner_inference", params_dir='./')
#         self.HD = ["Chương trình NER"]
#         self.ner_model_path = "/home/javis-ai/Javis_AI_UAT/api/weights/Ner/NlpHUST_electra-base-vn_v2"
#         self.load_then_save_to_yaml(file_path=f"{AppName}.yml")


# mPs_ner = Params_ner()
print = mPs_ner.mlog


class NERInference:
    """
    NER Inference Engine - Singleton (Eager Loading)
    Model được load ngay khi khởi tạo, không dùng thread.

    Usage:
        from NER.ner_inference import ner_engine, ner_predict

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
            text = ''.join(nums) if nums else text
        elif entity_type == "giờ_giao_dịch":
            m = self._digit_search.search(text)
            text = text[m.start():].strip() if m else text

        text = self._punct_pattern.sub('', text)

        return "" if self._special_only.fullmatch(text) else text

    def predict(self, text: str, max_len: int = 200) -> List[Dict[str, str]]:
        """
        Nhận diện entities trong text

        Args:
            text: Văn bản cần nhận diện
            max_len: Độ dài tối đa của sequence

        Returns:
            List các tuple (entity_type, entity_value)
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
        entities: List[Tuple[str, List[str]]] = []
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
                elif label.startswith("I-") and cur_type == label[2:]:
                    cur_tokens.append(words[word_idx])
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
                    result.append({etype: processed_value})

        return result

    def predict_dict(self, text: str, max_len: int = 200) -> List[Dict[str, str]]:
        """
        Nhận diện entities và trả về dạng list of dict

        Args:
            text: Văn bản cần nhận diện
            max_len: Độ dài tối đa của sequence

        Returns:
            List các dict {entity_type: entity_value}
        """
        return [{etype: value} for etype, value in self.predict(text, max_len)]

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
        >>> from NER.ner_inference import ner_predict
        >>> results = ner_predict("Xem giao dich cua stk 123456")
        >>> print(results)
        [{'Số_tài_khoản': '123456'}]
    """
    print(f"\n[NER] Câu gốc: {query}")
    result = ner_engine.predict_dict(query, max_len)
    print(f"[NER] Entities: {result}")
    return result


def ner_predict_raw(query: str, max_len: int = 200) -> List[Dict[str, str]]:
    """
    Predict NER entities và trả về dạng tuple (không log)

    Args:
        query: Văn bản cần nhận diện
        max_len: Độ dài tối đa

    Returns:
        List các tuple (entity_type, entity_value)
    """
    return ner_engine.predict(query, max_len)


# ============================================================
# Main cho testing
# ============================================================

if __name__ == "__main__":
    # Test
    test_query = 'Xem cac giao dich chuyen tien cua stk 2323423432 voi ghi chu chuyen tien cho ban'

    # Cách 1: Sử dụng hàm tiện ích
    results = ner_predict(test_query)

    # Cách 2: Sử dụng instance trực tiếp (đã load sẵn)
    results2 = ner_engine.predict(test_query)
    print(f"\n[NER] Results (tuple): {results2}")
