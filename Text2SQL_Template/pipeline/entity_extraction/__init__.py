from pipeline.entity_extraction.ner_local import extract_entities_local
from pipeline.entity_extraction.ner_fallback_llm import extract_entities_llm
from typing import Dict, Optional


def extract_entities(
    question: str,
    domain_id: Optional[str] = None,
    llm_generate_fn=None,
    use_llm_fallback: bool = False,
) -> Dict[str, str]:
    """
    Unified entity extraction: local regex first, optional LLM fallback.

    Args:
        question:         Câu hỏi tiếng Việt.
        domain_id:        ``"banking"`` | ``"hrm"``.
        llm_generate_fn:  LLM callable — required nếu ``use_llm_fallback=True``.
        use_llm_fallback: Nếu ``True`` và local NER trả về rỗng, thử LLM.

    Returns:
        Dict entity đã normalize.
    """
    result = extract_entities_local(question, domain_id=domain_id)
    if not result and use_llm_fallback and llm_generate_fn is not None:
        result = extract_entities_llm(
            question,
            llm_generate_fn=llm_generate_fn,
            domain_id=domain_id,
        )
    return result


__all__ = ["extract_entities", "extract_entities_local", "extract_entities_llm"]
