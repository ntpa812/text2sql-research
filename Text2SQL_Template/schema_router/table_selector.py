"""
Schema Router – Table Selector
Chọn bảng liên quan đến câu hỏi user bằng keyword matching + embedding similarity.
"""

import logging
import re
import unicodedata
from collections import defaultdict
from typing import List, Dict, Any

from config.settings import EMBEDDING_MODEL_NAME

logger = logging.getLogger(__name__)

# ─── Cached embedding model (singleton) ─────────────────────
_embed_model = None


def _normalize_text(text: str) -> str:
    text = (text or "").lower()
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text


# ─── Keyword-based table routing ────────────────────────────
# Mapping: keyword pattern → table names
DEFAULT_TABLE_KEYWORD_MAP: Dict[str, List[str]] = {
    r"giao dịch|chuyển tiền|chuyển khoản|thanh toán|transaction|sao kê|lịch sử giao dịch": [
        "transaction"
    ],
    r"tài khoản|account|số dư|balance|tk|stk": [
        "customer_account"
    ],
    r"khách hàng|customer|thông tin cá nhân|profile|họ tên|cccd|cmnd": [
        "customer"
    ],
    r"tiết kiệm|saving|gửi tiết kiệm": [
        "transaction", "customer_account"
    ],
    r"hóa đơn|bill|thanh toán hóa đơn|điện|nước|viễn thông": [
        "transaction"
    ],
    r"ngoại tệ|fx|đổi tiền|tỷ giá|exchange": [
        "transaction"
    ],
    r"đầu tư|investment|trái phiếu|chứng chỉ quỹ": [
        "transaction"
    ],
    r"vay|loan|khoản vay|trả nợ": [
        "transaction"
    ],
}


def _common_words(text1: str, text2: str) -> int:
    stopwords = {
        "của", "và", "là", "các", "cho", "trong", "từ", "đến", "với", "theo",
        "tôi", "có", "được", "để", "hay", "hoặc", "xem", "tra", "cứu",
    }
    words1 = set(re.findall(r"\w+", _normalize_text(text1))) - stopwords
    words2 = set(re.findall(r"\w+", _normalize_text(text2))) - stopwords
    return len(words1 & words2)


def _build_table_keyword_map(
    profiles: Dict[str, Any],
    table_keyword_map: Dict[str, List[str]] | None = None,
) -> Dict[str, List[str]]:
    if table_keyword_map:
        return table_keyword_map

    dynamic_map: Dict[str, List[str]] = defaultdict(list)
    for pattern, tables in DEFAULT_TABLE_KEYWORD_MAP.items():
        dynamic_map[pattern].extend(tables)

    for table_name, profile in profiles.items():
        keywords = {table_name, table_name.replace("_", " ")}
        for column in profile.get("columns", []):
            keywords.add(column.get("name", ""))
            keywords.update(column.get("suggested_keywords", []))
        for keyword in keywords:
            keyword = _normalize_text(str(keyword).strip())
            if keyword:
                dynamic_map[re.escape(keyword)].append(table_name)

    return {pattern: sorted(set(tables)) for pattern, tables in dynamic_map.items()}


def rank_tables_by_keyword(
    question: str,
    profiles: Dict[str, Any],
    table_keyword_map: Dict[str, List[str]] | None = None,
) -> List[Dict[str, Any]]:
    """Rank bảng dựa trên keyword matching + profile signal."""
    question_lower = _normalize_text(question)
    score_map: Dict[str, float] = defaultdict(float)
    match_map: Dict[str, List[str]] = defaultdict(list)

    resolved_map = _build_table_keyword_map(profiles, table_keyword_map)

    for pattern, tables in resolved_map.items():
        if re.search(_normalize_text(pattern), question_lower):
            for table in tables:
                score_map[table] += 2.0
                match_map[table].append(pattern)

    for table_name, profile in profiles.items():
        profile_text_parts = [table_name.replace("_", " ")]
        for column in profile.get("columns", []):
            profile_text_parts.append(column.get("description", ""))
            profile_text_parts.extend(column.get("suggested_keywords", []))
        score_map[table_name] += _common_words(question_lower, " ".join(profile_text_parts)) * 0.3

    if not score_map:
        return [
            {"table_name": table_name, "_score": 0.0, "_normalized_score": 0.0, "matched_patterns": []}
            for table_name in sorted(profiles.keys())
        ]

    max_score = max(score_map.values()) or 1.0
    ranked = [
        {
            "table_name": table_name,
            "_score": score,
            "_normalized_score": max(score, 0.0) / max_score,
            "matched_patterns": match_map.get(table_name, []),
        }
        for table_name, score in score_map.items()
    ]
    ranked.sort(key=lambda item: item["_score"], reverse=True)
    return ranked


def rank_tables(
    question: str,
    profiles: Dict[str, Any],
    use_embedding: bool = False,
    table_keyword_map: Dict[str, List[str]] | None = None,
) -> List[Dict[str, Any]]:
    """
    Rank bảng liên quan.
    - Bước 1: keyword matching (nhanh)
    - Bước 2 (optional): embedding similarity refine
    """
    ranked_tables = rank_tables_by_keyword(question, profiles, table_keyword_map)

    if use_embedding:
        ranked_tables = _refine_with_embedding(question, profiles, ranked_tables)

    return ranked_tables


def select_tables(
    question: str,
    profiles: Dict[str, Any],
    use_embedding: bool = False,
    table_keyword_map: Dict[str, List[str]] | None = None,
) -> List[str]:
    ranked_tables = rank_tables(
        question=question,
        profiles=profiles,
        use_embedding=use_embedding,
        table_keyword_map=table_keyword_map,
    )

    if not ranked_tables:
        return []

    filtered = [item["table_name"] for item in ranked_tables if item["_normalized_score"] >= 0.3]
    if filtered:
        return filtered
    return [ranked_tables[0]["table_name"]]


def _refine_with_embedding(
    question: str,
    profiles: Dict[str, Any],
    ranked_tables: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Optional: dùng embedding similarity để rank lại tables.
    Chỉ gọi khi use_embedding=True và sentence-transformers available.
    """
    try:
        from sentence_transformers import SentenceTransformer, util

        global _embed_model
        if _embed_model is None:
            logger.info("[Schema] Loading embedding model (one-time)...")
            _embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)

        q_emb = _embed_model.encode(f"query: {question}", convert_to_tensor=True)

        scored: List[Dict[str, Any]] = []
        max_score = 0.0
        for table_info in ranked_tables:
            tname = table_info["table_name"]
            profile = profiles.get(tname, {})
            # Tạo text đại diện cho bảng từ description của columns
            col_texts = [
                c.get("description", c["name"])
                for c in profile.get("columns", [])
            ]
            table_text = f"passage: {tname}: " + " ".join(col_texts[:20])
            t_emb = _embed_model.encode(table_text, convert_to_tensor=True)
            emb_score = util.cos_sim(q_emb, t_emb).item()
            combined_score = (table_info.get("_normalized_score", 0.0) * 0.7) + (max(emb_score, 0.0) * 0.3)
            max_score = max(max_score, combined_score)
            scored.append({
                **table_info,
                "_embedding_score": emb_score,
                "_score": combined_score,
            })

        scored.sort(key=lambda x: x["_score"], reverse=True)

        if max_score <= 0:
            for item in scored:
                item["_normalized_score"] = 0.0
        else:
            for item in scored:
                item["_normalized_score"] = item["_score"] / max_score
        return scored

    except ImportError:
        return ranked_tables
