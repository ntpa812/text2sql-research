"""
Intent Detection – Intent Ranker
Nhận diện intent từ câu hỏi user bằng keyword matching + embedding similarity.
"""

import os
import re
import pickle
import logging
from typing import Dict, List, Any, Optional

from config.settings import EMBEDDING_MODEL_NAME, EMBEDDING_CACHE_DIR

logger = logging.getLogger(__name__)

# ─── Cached embedding model (singleton) ─────────────────────
_embed_model = None
_intent_embeddings_cache: Dict[str, Any] = {}


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


def _get_embed_model():
    """Singleton embedding model."""
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("[Intent] Loading embedding model (one-time)...")
        _embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        logger.info("[Intent] Embedding model loaded.")
    return _embed_model


def _get_intent_embeddings(intent_index: List[Dict[str, Any]]):
    """Cache intent embeddings: compute once, save to disk."""
    global _intent_embeddings_cache

    cache_key = f"intent_emb_{len(intent_index)}"
    if cache_key in _intent_embeddings_cache:
        return _intent_embeddings_cache[cache_key]

    # Try load from disk
    os.makedirs(EMBEDDING_CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(EMBEDDING_CACHE_DIR, "intent_embeddings.pkl")

    if os.path.isfile(cache_file):
        try:
            with open(cache_file, "rb") as f:
                data = pickle.load(f)
            if data.get("count") == len(intent_index):
                logger.info(f"[Intent] Loaded cached intent embeddings ({len(intent_index)} intents)")
                _intent_embeddings_cache[cache_key] = data["embeddings"]
                return data["embeddings"]
        except Exception:
            pass

    # Compute embeddings
    model = _get_embed_model()
    passages = []
    for intent in intent_index:
        texts = [intent.get("description", "")]
        texts.extend(intent.get("keywords", []))
        texts.extend(intent.get("examples", [])[:3])
        passages.append("passage: " + " ".join(texts))

    logger.info(f"[Intent] Computing embeddings for {len(passages)} intents...")
    embeddings = model.encode(passages, convert_to_tensor=True, show_progress_bar=False)

    # Save to disk
    try:
        with open(cache_file, "wb") as f:
            pickle.dump({"count": len(intent_index), "embeddings": embeddings}, f)
        logger.info(f"[Intent] Saved intent embeddings to cache.")
    except Exception as e:
        logger.warning(f"[Intent] Could not save embeddings cache: {e}")

    _intent_embeddings_cache[cache_key] = embeddings
    return embeddings


def rank_by_embedding(
    question: str,
    intent_index: List[Dict[str, Any]],
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    """
    Rank intents bằng embedding similarity (sentence-transformers).
    Sử dụng cached embeddings (compute 1 lần duy nhất).
    Fallback sang keyword nếu không có model.
    """
    try:
        from sentence_transformers import util

        model = _get_embed_model()
        q_emb = model.encode(f"query: {question}", convert_to_tensor=True)
        intent_embs = _get_intent_embeddings(intent_index)

        scores = util.cos_sim(q_emb, intent_embs)[0]

        scored: List[Dict[str, Any]] = []
        for i, intent in enumerate(intent_index):
            scored.append({**intent, "_score": scores[i].item()})

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
