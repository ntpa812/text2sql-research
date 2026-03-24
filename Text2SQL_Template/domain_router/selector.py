"""
Domain Router – Selector
Chọn domain/database phù hợp bằng keyword + optional embedding.
"""

import logging
import re
import unicodedata
from typing import Dict, Any, List

from config.settings import EMBEDDING_MODEL_NAME

logger = logging.getLogger(__name__)

_embed_model = None


def _normalize_text(text: str) -> str:
    text = (text or "").lower()
    text = text.replace("đ", "d").replace("Đ", "D")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text


def _common_words(text1: str, text2: str) -> int:
    stopwords = {
        "của", "và", "là", "các", "cho", "trong", "từ", "đến", "với", "theo",
        "tôi", "có", "được", "để", "hay", "hoặc", "xem", "tra", "cứu",
    }
    words1 = set(re.findall(r"\w+", _normalize_text(text1))) - stopwords
    words2 = set(re.findall(r"\w+", _normalize_text(text2))) - stopwords
    return len(words1 & words2)


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("[DomainRouter] Loading embedding model (one-time)...")
        _embed_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    return _embed_model


def _score_by_keyword(question: str, domain: Dict[str, Any]) -> Dict[str, Any]:
    q = _normalize_text(question)
    raw_score = 0.0
    matched_keywords: List[str] = []

    for keyword in domain.get("keywords", []):
        kw = _normalize_text(keyword).strip()
        if kw and kw in q:
            raw_score += 2.0
            matched_keywords.append(keyword)

    for pattern in domain.get("keyword_patterns", []):
        if re.search(_normalize_text(pattern), q):
            raw_score += 2.5
            matched_keywords.append(pattern)

    reference_texts = [domain.get("display_name", ""), domain.get("description", "")]
    reference_texts.extend(domain.get("examples", [])[:5])
    raw_score += _common_words(q, " ".join(reference_texts)) * 0.3

    return {
        "domain_id": domain["domain_id"],
        "display_name": domain.get("display_name", domain["domain_id"]),
        "matched_keywords": sorted(set(matched_keywords)),
        "_keyword_score": raw_score,
    }


def _apply_embedding_scores(question: str, ranked: List[Dict[str, Any]], registry: Dict[str, Any]) -> List[Dict[str, Any]]:
    try:
        from sentence_transformers import util

        model = _get_embed_model()
        q_emb = model.encode(f"query: {question}", convert_to_tensor=True)

        max_score = 0.0
        for item in ranked:
            domain = registry["domains"][item["domain_id"]]
            texts = [domain.get("display_name", ""), domain.get("description", "")]
            texts.extend(domain.get("keywords", []))
            texts.extend(domain.get("examples", [])[:3])
            domain_text = "passage: " + " ".join(texts)
            d_emb = model.encode(domain_text, convert_to_tensor=True)
            emb_score = util.cos_sim(q_emb, d_emb).item()
            combined_score = (item["_keyword_normalized_score"] * 0.75) + (max(emb_score, 0.0) * 0.25)
            item["_embedding_score"] = emb_score
            item["_score"] = combined_score
            max_score = max(max_score, combined_score)

        if max_score <= 0:
            for item in ranked:
                item["_normalized_score"] = 0.0
        else:
            for item in ranked:
                item["_normalized_score"] = item["_score"] / max_score

        ranked.sort(key=lambda x: x["_score"], reverse=True)
        return ranked
    except ImportError:
        return ranked


def rank_domains(question: str, registry: Dict[str, Any], use_embedding: bool = False) -> List[Dict[str, Any]]:
    ranked = [_score_by_keyword(question, domain) for domain in registry.get("domains", {}).values()]
    ranked.sort(key=lambda x: x["_keyword_score"], reverse=True)

    max_keyword_score = max((item["_keyword_score"] for item in ranked), default=0.0) or 1.0
    for item in ranked:
        item["_keyword_normalized_score"] = max(item["_keyword_score"], 0.0) / max_keyword_score
        item["_score"] = item["_keyword_normalized_score"]
        item["_normalized_score"] = item["_keyword_normalized_score"]

    if use_embedding:
        ranked = _apply_embedding_scores(question, ranked, registry)

    return ranked


def shortlist_domains(ranked_domains: List[Dict[str, Any]], registry: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not ranked_domains:
        return []

    top = ranked_domains[0]
    if len(ranked_domains) == 1:
        return [top]

    second = ranked_domains[1]
    gap = top["_normalized_score"] - second["_normalized_score"]
    relative = (second["_normalized_score"] / top["_normalized_score"]) if top["_normalized_score"] > 0 else 0.0

    if gap < registry.get("shortlist_score_gap", 0.15) or relative >= registry.get("shortlist_relative_threshold", 0.7):
        return ranked_domains[:2]
    return [top]


def route_domains(
    question: str,
    registry: Dict[str, Any],
    use_embedding: bool = False,
    forced_domain: str | None = None,
) -> Dict[str, Any]:
    if forced_domain:
        forced = dict(registry["domains"][forced_domain])
        return {
            "ranked_domains": [{
                "domain_id": forced_domain,
                "display_name": forced.get("display_name", forced_domain),
                "_score": 1.0,
                "_normalized_score": 1.0,
                "_keyword_score": 1.0,
                "_keyword_normalized_score": 1.0,
                "matched_keywords": ["forced_domain"],
            }],
            "candidate_domains": [forced_domain],
            "selected_domain": forced_domain,
            "reason": "forced_domain",
        }

    ranked = rank_domains(question, registry, use_embedding=use_embedding)
    shortlist = shortlist_domains(ranked, registry)
    return {
        "ranked_domains": ranked,
        "candidate_domains": [item["domain_id"] for item in shortlist],
        "selected_domain": shortlist[0]["domain_id"] if shortlist else None,
        "reason": "score_shortlist",
    }
