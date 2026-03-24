"""
Intent Detection – Intent Ranker
Nhận diện intent từ câu hỏi user bằng keyword matching + embedding similarity.
"""

import os
import re
import pickle
import logging
import hashlib
import unicodedata
from typing import Dict, List, Any, Optional

from config.settings import EMBEDDING_MODEL_NAME, EMBEDDING_CACHE_DIR

logger = logging.getLogger(__name__)

# ─── Cached embedding model (singleton) ─────────────────────
_embed_model = None
_intent_embeddings_cache: Dict[str, Any] = {}


def _normalize_text(text: str) -> str:
    text = (text or "").lower()
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text


def _normalize_scored_items(scored: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not scored:
        return scored

    max_score = max(item.get("_score", 0.0) for item in scored) or 1.0
    for item in scored:
        item["_normalized_score"] = max(item.get("_score", 0.0), 0.0) / max_score
    return scored


def rank_by_keyword(question: str, intent_index: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Rank intents bằng keyword matching.
    Trả về list intents sorted by score (descending).
    """
    question_lower = _normalize_text(question)
    scored: List[Dict[str, Any]] = []

    for intent in intent_index:
        score = 0

        # Match keywords
        for kw in intent.get("keywords", []):
            if _normalize_text(kw) in question_lower:
                score += 2

        # Match partial words from examples
        for ex in intent.get("examples", [])[:5]:
            common = _common_words(question_lower, ex)
            score += common * 0.5

        # Match description
        desc = intent.get("description", "")
        common_desc = _common_words(question_lower, desc)
        score += common_desc * 0.3

        if score > 0:
            scored.append({**intent, "_score": score})

    scored.sort(key=lambda x: x["_score"], reverse=True)
    return _normalize_scored_items(scored)


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

    intent_signature = "|".join(
        sorted(f"{item.get('domain_id', '')}:{item.get('intent_id', '')}" for item in intent_index)
    )
    cache_hash = hashlib.sha256(intent_signature.encode("utf-8")).hexdigest()[:16]
    cache_key = f"intent_emb_{len(intent_index)}_{cache_hash}"
    if cache_key in _intent_embeddings_cache:
        return _intent_embeddings_cache[cache_key]

    # Try load from disk
    os.makedirs(EMBEDDING_CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(EMBEDDING_CACHE_DIR, f"intent_embeddings_{cache_hash}.pkl")

    if os.path.isfile(cache_file):
        try:
            with open(cache_file, "rb") as f:
                data = pickle.load(f)
            if data.get("count") == len(intent_index) and data.get("signature") == cache_hash:
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
            pickle.dump({"count": len(intent_index), "signature": cache_hash, "embeddings": embeddings}, f)
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
            raw_score = scores[i].item()
            normalized = max(min((raw_score + 1.0) / 2.0, 1.0), 0.0)
            scored.append({**intent, "_score": raw_score, "_normalized_score": normalized})

        scored.sort(key=lambda x: x["_score"], reverse=True)
        return scored[:top_k]

    except ImportError:
        return rank_by_keyword(question, intent_index)[:top_k]


def rank_intents(
    question: str,
    intent_index: List[Dict[str, Any]],
    use_embedding: bool = False,
    top_k: int = 3,
) -> List[Dict[str, Any]]:
    if use_embedding:
        return rank_by_embedding(question, intent_index, top_k=top_k)
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
    ranked = rank_intents(question, intent_index, use_embedding=use_embedding, top_k=1)

    if ranked:
        best = dict(ranked[0])
        best.pop("_score", None)
        best.pop("_normalized_score", None)
        return best

    return None


def _common_words(text1: str, text2: str) -> int:
    """Đếm số từ chung giữa 2 text (loại bỏ stopwords ngắn)."""
    stopwords = {"của", "và", "là", "các", "cho", "trong", "từ", "đến", "với", "theo", "tôi", "tôi", "có", "được", "để", "hay", "hoặc", "xem", "tra", "cứu"}
    words1 = set(_normalize_text(text1).split()) - stopwords
    words2 = set(_normalize_text(text2).split()) - stopwords
    return len(words1 & words2)
