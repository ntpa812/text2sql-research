"""
SQL Generation – LLM SQL Generator
Call Llama 3 (local via Ollama) để sinh SQL từ prompt.
Support 2 backend: ollama (recommended) hoặc transformers.
"""

import re
import json
import logging
from typing import Optional, Callable
from urllib.request import Request, urlopen
from urllib.error import URLError

from config.settings import (
    LLM_BACKEND,
    LLM_OLLAMA_BASE_URL,
    LLM_OLLAMA_MODEL,
    LLM_MODEL_PATH,
    LLM_MAX_NEW_TOKENS,
    LLM_TEMPERATURE,
)

logger = logging.getLogger(__name__)

# ─── Singleton model holder (transformers backend) ──────────
_model = None
_tokenizer = None


# ════════════════════════════════════════════════════════════
#  Ollama Backend (recommended)
# ════════════════════════════════════════════════════════════

def _generate_ollama(
    prompt: str,
    model: str = LLM_OLLAMA_MODEL,
    max_tokens: int = LLM_MAX_NEW_TOKENS,
    temperature: float = LLM_TEMPERATURE,
) -> str:
    """Call Llama 3 via Ollama REST API."""
    url = f"{LLM_OLLAMA_BASE_URL}/api/generate"
    payload = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": max_tokens,
            "temperature": temperature,
        },
    }).encode("utf-8")

    req = Request(url, data=payload, headers={"Content-Type": "application/json"})

    try:
        with urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("response", "")
    except URLError as e:
        raise RuntimeError(
            f"Ollama not reachable at {LLM_OLLAMA_BASE_URL}. "
            f"Make sure Ollama is running (`ollama serve`) and model is pulled (`ollama pull {model}`). "
            f"Error: {e}"
        )


# ════════════════════════════════════════════════════════════
#  Transformers Backend (fallback)
# ════════════════════════════════════════════════════════════

def _load_transformers_model():
    """Load Llama 3 via HuggingFace transformers (lazy singleton)."""
    global _model, _tokenizer

    if _model is not None:
        return

    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

    logger.info(f"[LLM] Loading transformers model from {LLM_MODEL_PATH}...")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )

    _tokenizer = AutoTokenizer.from_pretrained(
        LLM_MODEL_PATH,
        trust_remote_code=True,
    )

    _model = AutoModelForCausalLM.from_pretrained(
        LLM_MODEL_PATH,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    logger.info("[LLM] Transformers model loaded.")


def _generate_transformers(
    prompt: str,
    max_tokens: int = LLM_MAX_NEW_TOKENS,
    temperature: float = LLM_TEMPERATURE,
) -> str:
    """Generate via HuggingFace transformers."""
    import torch

    _load_transformers_model()

    inputs = _tokenizer(prompt, return_tensors="pt").to(_model.device)

    with torch.no_grad():
        outputs = _model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=temperature > 0,
        )

    return _tokenizer.decode(outputs[0], skip_special_tokens=True)


# ════════════════════════════════════════════════════════════
#  Public API
# ════════════════════════════════════════════════════════════

def generate_sql(
    prompt: str,
    max_new_tokens: int = LLM_MAX_NEW_TOKENS,
    temperature: float = LLM_TEMPERATURE,
) -> str:
    """
    Generate SQL từ prompt bằng Llama 3 local.
    Backend chọn qua LLM_BACKEND setting ("ollama" | "transformers").
    """
    if LLM_BACKEND == "ollama":
        raw = _generate_ollama(prompt, max_tokens=max_new_tokens, temperature=temperature)
    elif LLM_BACKEND == "transformers":
        raw = _generate_transformers(prompt, max_tokens=max_new_tokens, temperature=temperature)
    else:
        raise ValueError(f"Unknown LLM_BACKEND: {LLM_BACKEND}")

    sql = _extract_sql(raw, prompt)
    logger.info(f"[LLM] Generated SQL: {sql[:200]}...")
    return sql


def generate_sql_with_api(
    prompt: str,
    api_generate_fn: Callable[[str], str],
) -> str:
    """
    Generate SQL bằng external API (Colab, OpenAI, etc.).
    api_generate_fn: callable nhận prompt, trả về response string.
    """
    response = api_generate_fn(prompt)
    sql = _extract_sql(response, "")
    logger.info(f"[LLM-API] Generated SQL: {sql[:200]}...")
    return sql


def _extract_sql(response: str, prompt: str) -> str:
    """
    Extract SQL query từ LLM response.
    Loại bỏ prompt prefix, code fences, và text thừa.
    """
    # Loại bỏ prompt nếu response chứa cả prompt
    if prompt and response.startswith(prompt):
        response = response[len(prompt):]

    response = response.strip()

    # Loại bỏ markdown code fences
    code_block = re.search(r'```(?:sql)?\s*\n?(.*?)```', response, re.DOTALL | re.IGNORECASE)
    if code_block:
        response = code_block.group(1).strip()

    # Tìm SELECT statement
    select_match = re.search(r'(SELECT\s.+)', response, re.DOTALL | re.IGNORECASE)
    if select_match:
        sql = select_match.group(1).strip()
        # Cắt tại dấu chấm phẩy cuối cùng nếu có text sau
        semi_pos = sql.find(';')
        if semi_pos != -1:
            sql = sql[:semi_pos + 1]
        return sql

    return response.strip()
