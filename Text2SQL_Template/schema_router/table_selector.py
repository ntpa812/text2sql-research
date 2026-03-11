"""
Schema Router – Table Selector
Chọn bảng liên quan đến câu hỏi user bằng keyword matching + embedding similarity.
"""

import logging
import re
from typing import List, Dict, Any

from config.settings import EMBEDDING_MODEL_NAME

logger = logging.getLogger(__name__)

# ─── Cached embedding model (singleton) ─────────────────────
_embed_model = None


# ─── Keyword-based table routing ────────────────────────────
# Mapping: keyword pattern → table names
TABLE_KEYWORD_MAP: Dict[str, List[str]] = {
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


def select_tables_by_keyword(question: str) -> List[str]:
    """Chọn bảng dựa trên keyword matching."""
    question_lower = question.lower()
    matched: set = set()

    for pattern, tables in TABLE_KEYWORD_MAP.items():
        if re.search(pattern, question_lower):
            matched.update(tables)

    # Default: nếu không match gì → trả về tất cả
    if not matched:
        matched = {"transaction", "customer_account", "customer"}

    return sorted(matched)


def select_tables(
    question: str,
    profiles: Dict[str, Any],
    use_embedding: bool = False,
) -> List[str]:
    """
    Chọn bảng liên quan.
    - Bước 1: keyword matching (nhanh)
    - Bước 2 (optional): embedding similarity refine
    """
    tables = select_tables_by_keyword(question)

    if use_embedding:
        tables = _refine_with_embedding(question, profiles, tables)

    return tables


def _refine_with_embedding(
    question: str,
    profiles: Dict[str, Any],
    candidate_tables: List[str],
) -> List[str]:
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

        scored: List[tuple] = []
        for tname in candidate_tables:
            profile = profiles.get(tname, {})
            # Tạo text đại diện cho bảng từ description của columns
            col_texts = [
                c.get("description", c["name"])
                for c in profile.get("columns", [])
            ]
            table_text = f"passage: {tname}: " + " ".join(col_texts[:20])
            t_emb = _embed_model.encode(table_text, convert_to_tensor=True)
            score = util.cos_sim(q_emb, t_emb).item()
            scored.append((tname, score))

        scored.sort(key=lambda x: x[1], reverse=True)

        # Giữ table có score > 0.3 hoặc ít nhất 1 table
        result = [t for t, s in scored if s > 0.3]
        if not result:
            result = [scored[0][0]] if scored else candidate_tables

        return result

    except ImportError:
        return candidate_tables
