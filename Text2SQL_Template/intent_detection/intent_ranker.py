"""
Intent Detection – Intent Ranker
Nhận diện intent từ câu hỏi user bằng keyword matching + embedding similarity.
"""

import re
from typing import Dict, List, Any, Optional

from config.settings import EMBEDDING_MODEL_NAME


def rank_by_keyword(question: str, intent_index: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank intents bằng keyword matching.
    Trả về list intents sorted by score (descending).
    """
    question_lower = question.lower()
    scored: List[Dict[str, Any]] = []

    for intent in intent_index:
        score = 0

        # Match keywords
        for kw in intent.get("keywords", []):
            if kw.lower() in question_lower:
                score += 2

        # Match partial words from examples
        for ex in intent.get("examples", [])[:5]:
            common = _common_words(question_lower, ex.lower())
            score += common * 0.5

        # Match description
        desc = intent.get("description", "").lower()
        common_desc = _common_words(question_lower, desc)
        score += common_desc * 0.3

        if score > 0:
            scored.append({**intent, "_score": score})

    scored.sort(key=lambda x: x["_score"], reverse=True)
    return scored


def rank_by_embedding(
    question: str,
    intent_index: List[Dict[str, Any]],
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """
    Rank intents bằng embedding similarity (sentence-transformers).
    Fallback sang keyword nếu không có model.
    """
    try:
        from sentence_transformers import SentenceTransformer, util

        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        q_emb = model.encode(f"query: {question}", convert_to_tensor=True)

        scored: List[Dict[str, Any]] = []
        for intent in intent_index:
            # Combine description + keywords + first few examples
            texts = [intent.get("description", "")]
            texts.extend(intent.get("keywords", []))
            texts.extend(intent.get("examples", [])[:3])
            passage = "passage: " + " ".join(texts)

            p_emb = model.encode(passage, convert_to_tensor=True)
            score = util.cos_sim(q_emb, p_emb).item()
            scored.append({**intent, "_score": score})

        scored.sort(key=lambda x: x["_score"], reverse=True)
        return scored[:top_k]

    except ImportError:
        return rank_by_keyword(question, intent_index)[:top_k]


def detect_intent(
    question: str,
    intent_index: List[Dict[str, Any]],
    use_embedding: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Detect intent chính từ câu hỏi.
    Trả về intent match tốt nhất hoặc None.
    """
    if use_embedding:
        ranked = rank_by_embedding(question, intent_index, top_k=1)
    else:
        ranked = rank_by_keyword(question, intent_index)

    if ranked:
        best = ranked[0]
        best.pop("_score", None)
        return best

    return None


def _common_words(text1: str, text2: str) -> int:
    """Đếm số từ chung giữa 2 text (loại bỏ stopwords ngắn)."""
    stopwords = {"của", "và", "là", "các", "cho", "trong", "từ", "đến", "với", "theo", "tôi", "tôi", "có", "được", "để", "hay", "hoặc", "xem", "tra", "cứu"}
    words1 = set(text1.split()) - stopwords
    words2 = set(text2.split()) - stopwords
    return len(words1 & words2)
"""
Intent Detection – Intent Ranker
Nhận diện intent từ câu hỏi user bằng keyword matching + embedding similarity.
"""

import re
from typing import Dict, List, Any, Optional

from config.settings import EMBEDDING_MODEL_NAME


def rank_by_keyword(question: str, intent_index: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank intents bằng keyword matching.
    Trả về list intents sorted by score (descending).
    """
    question_lower = question.lower()
    scored: List[Dict[str, Any]] = []

    for intent in intent_index:
        score = 0

        # Match keywords
        for kw in intent.get("keywords", []):
            if kw.lower() in question_lower:
                score += 2

        # Match partial words from examples
        for ex in intent.get("examples", [])[:5]:
            common = _common_words(question_lower, ex.lower())
            score += common * 0.5

        # Match description
        desc = intent.get("description", "").lower()
        common_desc = _common_words(question_lower, desc)
        score += common_desc * 0.3

        if score > 0:
            scored.append({**intent, "_score": score})

    scored.sort(key=lambda x: x["_score"], reverse=True)
    return scored


def rank_by_embedding(
    question: str,
    intent_index: List[Dict[str, Any]],
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """
    Rank intents bằng embedding similarity (sentence-transformers).
    Fallback sang keyword nếu không có model.
    """
    try:
        from sentence_transformers import SentenceTransformer, util

        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        q_emb = model.encode(f"query: {question}", convert_to_tensor=True)

        scored: List[Dict[str, Any]] = []
        for intent in intent_index:
            # Combine description + keywords + first few examples
            texts = [intent.get("description", "")]
            texts.extend(intent.get("keywords", []))
            texts.extend(intent.get("examples", [])[:3])
            passage = "passage: " + " ".join(texts)

            p_emb = model.encode(passage, convert_to_tensor=True)
            score = util.cos_sim(q_emb, p_emb).item()
            scored.append({**intent, "_score": score})

        scored.sort(key=lambda x: x["_score"], reverse=True)
        return scored[:top_k]

    except ImportError:
        return rank_by_keyword(question, intent_index)[:top_k]


def detect_intent(
    question: str,
    intent_index: List[Dict[str, Any]],
    use_embedding: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Detect intent chính từ câu hỏi.
    Trả về intent match tốt nhất hoặc None.
    """
    if use_embedding:
        ranked = rank_by_embedding(question, intent_index, top_k=1)
    else:
        ranked = rank_by_keyword(question, intent_index)

    if ranked:
        best = ranked[0]
        best.pop("_score", None)
        return best

    return None


def _common_words(text1: str, text2: str) -> int:
    """Đếm số từ chung giữa 2 text (loại bỏ stopwords ngắn)."""
    stopwords = {"của", "và", "là", "các", "cho", "trong", "từ", "đến", "với", "theo", "tôi", "tôi", "có", "được", "để", "hay", "hoặc", "xem", "tra", "cứu"}
    words1 = set(text1.split()) - stopwords
    words2 = set(text2.split()) - stopwords
    return len(words1 & words2)
