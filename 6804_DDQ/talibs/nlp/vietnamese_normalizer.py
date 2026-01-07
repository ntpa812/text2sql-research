"""
Vietnamese Text Normalizer
==========================
Pipeline 5 giai đoạn xử lý văn bản tiếng Việt:
1. Text Cleaning - Chuẩn hóa Unicode, xử lý emoji, ký tự đặc biệt
2. Keyboard Typo Correction - Sửa lỗi gõ Telex/VNI
3. Teencode & Abbreviation Expansion - Mở rộng viết tắt
4. Diacritics Restoration - Khôi phục dấu tiếng Việt (optional)
5. Query Rewriting - Viết lại câu truy vấn tối ưu cho RAG (optional)

Author: AI Assistant
Version: 1.0
"""

import re
import json
import unicodedata
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass


@dataclass
class NormalizationResult:
    """Kết quả chuẩn hóa văn bản"""
    original: str
    normalized: str
    stages_applied: List[str]
    changes: Dict[str, str]  # Mapping từ gốc -> từ đã sửa
    confidence: float = 1.0


class VietnameseTextNormalizer:
    """
    Class chuẩn hóa văn bản tiếng Việt

    Sử dụng:
        from core.nlp import VietnameseTextNormalizer
        normalizer = VietnameseTextNormalizer(params)

        # Chuẩn hóa cho Intent Recognition
        result = normalizer.normalize_for_intent(text)

        # Chuẩn hóa cho RAG Search
        result = normalizer.normalize_for_rag(text)

        # Lấy stopwords cho BM25
        stopwords = normalizer.get_stopwords()
    """

    def __init__(self, params=None):
        """
        Khởi tạo normalizer

        Args:
            params: Params_VietnameseNormalizer instance từ config.py
                    Nếu None, sẽ dùng default config
        """
        self.params = params
        self.logger = logging.getLogger(__name__)

        # Load dictionaries
        self._load_dictionaries()

        # Compile regex patterns
        self._compile_patterns()

        self.logger.info("[VietnameseNormalizer] Initialized successfully")

    def _load_dictionaries(self):
        """Load tất cả dictionary files"""
        if self.params:
            dict_dir = Path(self.params.dict_dir)
        else:
            dict_dir = Path(__file__).parent / "dictionaries"

        # Teencode dictionary
        self.teencode_dict = self._load_json(dict_dir / "teencode_dict.json", "mappings", {})

        # Banking abbreviations
        self.banking_abbr = self._load_json(dict_dir / "banking_abbreviations.json", "mappings", {})

        # Keyboard typos - Telex
        keyboard_data = self._load_json(dict_dir / "keyboard_typos.json", None, {})
        self.telex_errors = keyboard_data.get("telex_patterns", {}).get("common_errors", {})
        self.vni_errors = keyboard_data.get("vni_patterns", {}).get("common_errors", {})
        self.banking_typos = keyboard_data.get("special_cases", {}).get("banking_typos", {})

        # Stopwords
        stopwords_data = self._load_json(dict_dir / "stopwords_vi.json", None, {})
        self.stopwords = set(stopwords_data.get("stopwords", []))

        # Add custom stopwords from params
        if self.params and hasattr(self.params, 'custom_stopwords'):
            self.stopwords.update(self.params.custom_stopwords)

        self.logger.info(f"[VietnameseNormalizer] Loaded: teencode={len(self.teencode_dict)}, "
                        f"banking_abbr={len(self.banking_abbr)}, "
                        f"telex_errors={len(self.telex_errors)}, "
                        f"stopwords={len(self.stopwords)}")

    def _load_json(self, path: Path, key: Optional[str], default):
        """Load JSON file with error handling"""
        try:
            if path.exists():
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if key:
                        return data.get(key, default)
                    return data
            else:
                self.logger.warning(f"[VietnameseNormalizer] File not found: {path}")
                return default
        except Exception as e:
            self.logger.error(f"[VietnameseNormalizer] Error loading {path}: {e}")
            return default

    def _compile_patterns(self):
        """Compile regex patterns for performance"""
        # Emoji pattern
        self.emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE
        )

        # Multiple whitespace
        self.whitespace_pattern = re.compile(r'\s+')

        # Special characters (keep Vietnamese diacritics)
        self.special_chars_pattern = re.compile(r'[^\w\sàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]', re.UNICODE)

        # Telex double vowel patterns
        self.telex_vowel_patterns = {
            'aa': 'â', 'aw': 'ă', 'ee': 'ê', 'oo': 'ô',
            'ow': 'ơ', 'uw': 'ư', 'dd': 'đ',
            'AA': 'Â', 'AW': 'Ă', 'EE': 'Ê', 'OO': 'Ô',
            'OW': 'Ơ', 'UW': 'Ư', 'DD': 'Đ'
        }

    # ========================================================================
    # Stage 1: Text Cleaning
    # ========================================================================

    def _clean_text(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Stage 1: Text Cleaning
        - Normalize Unicode to NFC
        - Remove emojis
        - Normalize whitespace
        - Optional lowercase
        """
        changes = {}
        original = text

        # Unicode NFC normalization
        if self.params is None or self.params.normalize_unicode:
            text = unicodedata.normalize('NFC', text)

        # Remove emojis
        if self.params is None or self.params.remove_emoji:
            text = self.emoji_pattern.sub(' ', text)

        # Normalize whitespace
        if self.params is None or self.params.normalize_whitespace:
            text = self.whitespace_pattern.sub(' ', text).strip()

        # Lowercase (optional - may need original case for some use cases)
        if self.params and self.params.lowercase:
            text = text.lower()

        if original != text:
            changes['text_cleaning'] = f"{original[:50]}... -> {text[:50]}..."

        return text, changes

    # ========================================================================
    # Stage 2: Keyboard Typo Correction
    # ========================================================================

    def _fix_keyboard_typos(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Stage 2: Sửa lỗi gõ bàn phím Telex/VNI
        - nhuxng -> những
        - tieenf -> tiền
        - nhu7ng -> những (VNI)
        """
        if self.params and not self.params.enable_keyboard_typo:
            return text, {}

        changes = {}

        # First, handle multi-word banking phrases (sorted by length, longest first)
        text_lower = text.lower()
        sorted_phrases = sorted(self.banking_typos.keys(), key=len, reverse=True)
        for phrase in sorted_phrases:
            if phrase in text_lower:
                replacement = self.banking_typos[phrase]
                # Find the phrase case-insensitively and replace
                pattern = re.compile(re.escape(phrase), re.IGNORECASE)
                if pattern.search(text):
                    text = pattern.sub(replacement, text)
                    text_lower = text.lower()  # Update for next iteration
                    changes[phrase] = replacement

        # Then handle single-word corrections
        words = text.split()
        corrected_words = []

        for word in words:
            original_word = word
            word_lower = word.lower()

            # Check Telex errors
            if self.params is None or self.params.telex_correction:
                if word_lower in self.telex_errors:
                    word = self.telex_errors[word_lower]
                    changes[original_word] = word

            # Check VNI errors
            if self.params is None or self.params.vni_correction:
                if word_lower in self.vni_errors:
                    word = self.vni_errors[word_lower]
                    changes[original_word] = word

            corrected_words.append(word)

        return ' '.join(corrected_words), changes

    # ========================================================================
    # Stage 3: Teencode & Abbreviation Expansion
    # ========================================================================

    def _expand_abbreviations(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Stage 3: Mở rộng teencode và viết tắt
        - ko -> không
        - CCTG -> chứng chỉ tiền gửi
        """
        changes = {}
        words = text.split()
        expanded_words = []

        min_len = 2
        if self.params and hasattr(self.params, 'min_word_length_for_abbr'):
            min_len = self.params.min_word_length_for_abbr

        # Punctuation to strip when checking abbreviations
        punct = '?.,!;:'

        for word in words:
            original_word = word
            word_lower = word.lower()

            # Strip punctuation for matching
            word_clean = word_lower.rstrip(punct)
            trailing_punct = word_lower[len(word_clean):]  # Keep trailing punctuation

            # Skip very short words
            if len(word_clean) < min_len:
                expanded_words.append(word)
                continue

            # Check teencode
            if self.params is None or self.params.enable_teencode_expansion:
                if word_clean in self.teencode_dict:
                    replacement = self.teencode_dict[word_clean] + trailing_punct
                    changes[original_word] = replacement
                    expanded_words.append(replacement)
                    continue

            # Check banking abbreviations
            if self.params is None or self.params.enable_banking_abbreviation:
                if word_clean in self.banking_abbr:
                    replacement = self.banking_abbr[word_clean] + trailing_punct
                    changes[original_word] = replacement
                    expanded_words.append(replacement)
                    continue

            expanded_words.append(word)

        return ' '.join(expanded_words), changes

    # ========================================================================
    # Stage 4: Diacritics Restoration (Optional)
    # ========================================================================

    def _restore_diacritics(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Stage 4: Khôi phục dấu tiếng Việt
        - nguoi -> người
        - tien -> tiền

        NOTE: Cần model vn-accent-restorer, hiện tại chỉ dùng simple mapping
        """
        if self.params and not self.params.enable_diacritics_restoration:
            return text, {}

        # TODO: Integrate với vn-accent-restorer model
        # Hiện tại dùng simple rule-based approach

        changes = {}
        # Simple diacritics mappings (common cases)
        simple_mappings = {
            'nguoi': 'người',
            'tien': 'tiền',
            'duoc': 'được',
            'khong': 'không',
            'cung': 'cũng',
            'nhung': 'những',
            'nay': 'này',
            'day': 'đây',
            'do': 'đó',
            'cua': 'của',
            'vao': 'vào',
            'la': 'là',
            'co': 'có',
            'tai': 'tại',
            've': 'về',
            'the': 'thế',
            'mot': 'một',
            'cho': 'cho',
            'gia': 'giá',
            'lai': 'lại',
            'de': 'để',
            'phai': 'phải',
            'biet': 'biết',
            'can': 'cần',
            'muon': 'muốn',
            'lon': 'lớn',
            'nho': 'nhỏ',
            'dung': 'đúng',
            'sai': 'sai',
            'tiet': 'tiết',
            'kiem': 'kiếm',
            'suat': 'suất',
            'ky': 'kỳ',
            'han': 'hạn',
            'vay': 'vay',
            'gui': 'gửi',
            'rut': 'rút',
            'nop': 'nộp',
            'chuyen': 'chuyển',
            'khoan': 'khoản',
            'ngan': 'ngân',
            'hang': 'hàng',
            'the': 'thẻ',
            'tin': 'tín',
            'so': 'số',
            'du': 'dư',
            'no': 'nợ',
            'tra': 'trả',
            'quyen': 'quyền',
            'loi': 'lợi',
            'dieu': 'điều',
            'chung': 'chứng',
            'chi': 'chỉ',
            'phat': 'phát',
            'hanh': 'hành'
        }

        words = text.split()
        restored_words = []

        for word in words:
            word_lower = word.lower()
            if word_lower in simple_mappings:
                new_word = simple_mappings[word_lower]
                changes[word] = new_word
                restored_words.append(new_word)
            else:
                restored_words.append(word)

        return ' '.join(restored_words), changes

    # ========================================================================
    # Stage 5: Query Rewriting (Optional, for RAG)
    # ========================================================================

    def _rewrite_query(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Stage 5: Viết lại câu truy vấn tối ưu cho RAG

        NOTE: Cần LLM, hiện tại chỉ thực hiện simple normalization
        """
        if self.params and not self.params.enable_query_rewriting:
            return text, {}

        # TODO: Integrate với LLM để rewrite query
        # Hiện tại chỉ return nguyên bản

        changes = {}
        return text, changes

    # ========================================================================
    # Public API Methods
    # ========================================================================

    def normalize(self, text: str, stages: Optional[List[str]] = None) -> NormalizationResult:
        """
        Normalize văn bản với các stages được chỉ định

        Args:
            text: Văn bản cần chuẩn hóa
            stages: List các stage cần chạy.
                    None = chạy tất cả stages được bật trong config
                    Options: ['cleaning', 'keyboard', 'abbreviation', 'diacritics', 'rewriting']

        Returns:
            NormalizationResult với thông tin chi tiết
        """
        if not text or not text.strip():
            return NormalizationResult(
                original=text,
                normalized=text,
                stages_applied=[],
                changes={},
                confidence=1.0
            )

        original = text
        all_changes = {}
        applied_stages = []

        # Stage 1: Text Cleaning
        if stages is None or 'cleaning' in stages:
            text, changes = self._clean_text(text)
            if changes:
                all_changes.update(changes)
                applied_stages.append('cleaning')

        # Stage 2: Keyboard Typo Correction
        if stages is None or 'keyboard' in stages:
            text, changes = self._fix_keyboard_typos(text)
            if changes:
                all_changes.update(changes)
                applied_stages.append('keyboard')

        # Stage 3: Teencode & Abbreviation Expansion
        if stages is None or 'abbreviation' in stages:
            text, changes = self._expand_abbreviations(text)
            if changes:
                all_changes.update(changes)
                applied_stages.append('abbreviation')

        # Stage 4: Diacritics Restoration
        if stages is None or 'diacritics' in stages:
            text, changes = self._restore_diacritics(text)
            if changes:
                all_changes.update(changes)
                applied_stages.append('diacritics')

        # Stage 5: Query Rewriting
        if stages is None or 'rewriting' in stages:
            text, changes = self._rewrite_query(text)
            if changes:
                all_changes.update(changes)
                applied_stages.append('rewriting')

        # Log if enabled
        if self.params and self.params.log_normalized_queries and all_changes:
            self.logger.info(f"[Normalize] '{original}' -> '{text}' | Changes: {all_changes}")

        return NormalizationResult(
            original=original,
            normalized=text,
            stages_applied=applied_stages,
            changes=all_changes,
            confidence=1.0 if not all_changes else 0.95
        )

    def normalize_for_intent(self, text: str) -> str:
        """
        Chuẩn hóa văn bản cho Intent Recognition

        Stages: cleaning, keyboard, abbreviation
        (Không cần diacritics restoration vì model đã train với nhiều variants)

        Returns:
            Văn bản đã chuẩn hóa
        """
        result = self.normalize(text, stages=['cleaning', 'keyboard', 'abbreviation'])
        return result.normalized

    def normalize_for_rag(self, text: str) -> str:
        """
        Chuẩn hóa văn bản cho RAG Search

        Stages: cleaning, keyboard, abbreviation, diacritics (if enabled)

        Returns:
            Văn bản đã chuẩn hóa
        """
        stages = ['cleaning', 'keyboard', 'abbreviation']
        if self.params and self.params.enable_diacritics_restoration:
            stages.append('diacritics')

        result = self.normalize(text, stages=stages)
        return result.normalized

    def normalize_for_bm25(self, text: str) -> str:
        """
        Chuẩn hóa và loại bỏ stopwords cho BM25

        Returns:
            Văn bản đã chuẩn hóa và loại stopwords
        """
        # First normalize
        normalized = self.normalize_for_rag(text)

        # Then remove stopwords
        words = normalized.split()
        filtered_words = [w for w in words if w.lower() not in self.stopwords]

        return ' '.join(filtered_words)

    def get_stopwords(self) -> set:
        """
        Lấy danh sách stopwords cho BM25

        Returns:
            Set of stopwords
        """
        return self.stopwords.copy()

    def extract_keywords(self, text: str) -> List[str]:
        """
        Trích xuất keywords từ văn bản (loại bỏ stopwords)

        Args:
            text: Văn bản đầu vào

        Returns:
            List các keywords
        """
        normalized = self.normalize_for_rag(text)
        words = normalized.split()
        keywords = [w for w in words if w.lower() not in self.stopwords and len(w) > 1]
        return keywords

    def get_normalization_info(self, text: str) -> dict:
        """
        Lấy thông tin chi tiết về quá trình chuẩn hóa

        Returns:
            Dict với thông tin chi tiết từng stage
        """
        result = self.normalize(text)
        return {
            'original': result.original,
            'normalized': result.normalized,
            'stages_applied': result.stages_applied,
            'changes': result.changes,
            'confidence': result.confidence,
            'keywords': self.extract_keywords(text)
        }


# Singleton instance (sẽ được khởi tạo khi import module lần đầu)
_normalizer_instance = None


def get_normalizer(params=None) -> VietnameseTextNormalizer:
    """
    Factory function để lấy singleton instance của normalizer

    Args:
        params: Params_VietnameseNormalizer instance (optional)

    Returns:
        VietnameseTextNormalizer instance
    """
    global _normalizer_instance
    if _normalizer_instance is None:
        _normalizer_instance = VietnameseTextNormalizer(params)
    return _normalizer_instance
