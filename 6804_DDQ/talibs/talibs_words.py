# coding: utf-8

import re
import unicodedata
import math
from collections import Counter, defaultdict
from typing import List, Iterable

from tatools01.ParamsBase import TactParameters

AppName = 'DDQ_dynamic_data_query'


# =====================================================
# 1) PARAMS CLASS — GIỮ NGUYÊN ĐÚNG THEO YÊU CẦU
# =====================================================

class Params_01(TactParameters):
    def __init__(self):
        super().__init__(ModuleName="talibs_words", params_dir='./')

        # ===== Stopwords mặc định =====
        self.stopwords = [
            "là","của","và","hoặc","thì","lại","nữa","nhé","à","ạ","nhỉ",
            "các","những","một","tôi","bạn","anh","chị","em","chúng","ta","họ",
            "để","trong","khi","với","đến","tại","cho","ra","vào",
            "được","bị","sẽ","đã","rồi","đó","này","kia","ấy","nên"
        ]

        # ===== Phrases mặc định =====
        self.common_phrases = [
            "tài khoản", "số dư", "dư nợ", "khoản vay", "thẻ tín dụng",
            "chuyển khoản", "ghi nợ", "ghi có", "lãi suất", "hạn mức",
            "truy vấn", "xác thực", "định danh", "chữ ký số"
        ]

        # ===== Stem rules mặc định =====
        self.stem_rules = {
            "kiểm": ["kiểm", "kiểm tra", "kiểm soát"],
            "truy": ["truy", "truy vấn"],
            "vấn": ["vấn", "vấn tin"],
            "nợ": ["nợ", "dư nợ"],
            "dư": ["dư", "số dư"],
            "chuyển": ["chuyển", "chuyển khoản"],
            "khoản": ["khoản", "khoản vay"],
        }

        # Load file nếu có, nếu không thì tạo, rồi save lại
        self.load_then_save_to_yaml(file_path=f"{AppName}.yml")


# INSTANCE CONFIG TOÀN CỤC
config = Params_01()


# =====================================================
# 2) HÀM CHUẨN HÓA VÀ TOKENIZE CƠ BẢN
# =====================================================

def normalize_unicode(text: str) -> str:
    return unicodedata.normalize("NFC", text)

def remove_diacritics(text: str) -> str:
    base = unicodedata.normalize("NFD", text)
    return "".join(c for c in base if unicodedata.category(c) != "Mn")

def clean_text_basic(text: str) -> str:
    text = normalize_unicode(text.lower())
    return re.sub(r'[^\w\s]', ' ', text)

def simple_tokenize(text: str) -> List[str]:
    if not text:
        return []
    return clean_text_basic(text).split()


# =====================================================
# 3) AUTO LEARNING: STOPWORDS + PHRASES + STEMS
# =====================================================

def learn_from_corpus(
    corpus: Iterable[str],
    min_phrase_count: int = 3,
    pmi_threshold: float = 3.0,
    stopword_df_threshold: float = 0.85
):
    """
    Tự học stopwords, phrases, stem_rules từ corpus.
    Sau đó MERGE với rule cũ trong config.
    Cuối cùng gọi config.save_to_yaml_only().
    """

    docs = list(corpus)
    ndocs = len(docs)

    unigram = Counter()
    ngram = Counter()
    df = Counter()

    # ----------------------------------------------
    # COUNT
    # ----------------------------------------------
    for doc in docs:
        toks = simple_tokenize(doc)
        seen = set()

        for t in toks:
            unigram[t] += 1
            seen.add(t)

        for t in seen:
            df[t] += 1

        L = len(toks)
        for n in (2, 3):
            for i in range(L - n + 1):
                ng = " ".join(toks[i:i+n])
                ngram[ng] += 1

    total_tokens = sum(unigram.values())

    # ----------------------------------------------
    # AUTO PHRASES (PMI)
    # ----------------------------------------------
    learned_phrases = set()

    for ng, cnt in ngram.items():
        if cnt < min_phrase_count:
            continue
        parts = ng.split()
        denom = 1
        for p in parts:
            denom *= max(1, unigram.get(p, 1))

        score = math.log((cnt * total_tokens) / denom + 1e-9)

        if score >= pmi_threshold:
            learned_phrases.add(ng.replace(" ", "_"))

    # merge với phrase mặc định
    default_phrases = {p.replace(" ", "_") for p in config.common_phrases}
    merged_phrases = default_phrases | learned_phrases

    # ----------------------------------------------
    # AUTO STOPWORDS (document frequency)
    # ----------------------------------------------
    learned_stopwords = set()

    for token, dcount in df.items():
        if (dcount / ndocs) >= stopword_df_threshold and len(token) <= 3:
            learned_stopwords.add(token)

    merged_stopwords = set(config.stopwords) | learned_stopwords

    # ----------------------------------------------
    # AUTO STEM RULES
    # ----------------------------------------------
    stem_groups = defaultdict(list)

    for token in unigram:
        base = remove_diacritics(token)
        stem_groups[base].append((token, unigram[token]))

    learned_stems = {}

    for base, items in stem_groups.items():
        if len(items) <= 1:
            continue
        items_sorted = sorted(items, key=lambda x: (-x[1], len(x[0])))
        stem = items_sorted[0][0]
        variants = [v for v, _ in items]
        learned_stems[stem] = variants

    # MERGE stem rules
    merged_stems = dict(config.stem_rules)
    for stem, vars in learned_stems.items():
        if stem in merged_stems:
            merged_stems[stem] = list(set(merged_stems[stem] + vars))
        else:
            merged_stems[stem] = vars

    # ----------------------------------------------
    # LƯU VÀO CONFIG
    # ----------------------------------------------
    config.stopwords = list(sorted(list(merged_stopwords)))
    config.common_phrases = list(sorted(list(merged_phrases)))
    config.stem_rules = merged_stems

    config.save_to_yaml_only()


# =====================================================
# 4) TOKENIZE THÔNG MINH
# =====================================================

def apply_phrase_protection(text: str) -> str:
    """
    Biến phrase (vd: tài khoản) → tài_khoản để bảo vệ khi tokenize.
    """
    out = text
    phrases = sorted(config.common_phrases, key=lambda x: -len(x))

    for ph in phrases:
        spaced = ph.replace("_", " ")
        out = re.sub(r'\b' + re.escape(spaced) + r'\b', ph, out)

    return out


def stem_single_token(t: str) -> str:
    """
    Stem theo config.stem_rules + fallback bằng remove_diacritics
    """
    for stem, variants in config.stem_rules.items():
        if t == stem or t in variants:
            return stem
        if remove_diacritics(t) == remove_diacritics(stem):
            return stem
    return remove_diacritics(t) if len(t) > 3 else t


# =====================================================
# 5) HÀM CHÍNH: tokenize_vietnamese_best
# =====================================================

def tokenize_vietnamese_best(text: str) -> List[str]:
    """
    Token thông minh:
    - token gốc
    - stem
    - no-diacritics
    - bigram/trigram
    """
    if not text:
        return []

    # 1) normalize
    text = normalize_unicode(text.lower())

    # 2) phrase protect
    text = apply_phrase_protection(text)

    # 3) remove punctuation
    text = re.sub(r'[^\w\s_]', ' ', text)

    # 4) split
    tokens = text.split()

    # 5) remove stopwords
    tokens = [t for t in tokens if t not in config.stopwords]

    # 6) stemming
    stems = [stem_single_token(t) for t in tokens]

    # 7) no-diacritic semantic tokens
    no_diac = [remove_diacritics(t) for t in stems]

    output = stems + no_diac

    # 8) add ngram bigram/trigram
    for n in (2, 3):
        for i in range(len(stems) - n + 1):
            ng = "_".join(stems[i:i+n])
            output.append(ng)

    # 9) unique + remove 1-char tokens
    final = list(dict.fromkeys([t for t in output if len(t) > 1]))

    return final
