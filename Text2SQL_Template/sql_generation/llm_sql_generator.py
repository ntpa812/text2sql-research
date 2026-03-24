"""
SQL Generation – LLM SQL Generator
Sinh SQL tu prompt voi nhieu backend LLM.
Support: openai_compatible, ollama, transformers.
"""

import re
import json
import logging
from typing import Optional, Callable, Dict, Any
from urllib.request import Request, urlopen
from urllib.error import URLError

from config.settings import (
    LLM_BACKEND,
    LLM_API_BASE_URL,
    LLM_API_KEY,
    LLM_API_MODEL,
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
_last_generation_info: Dict[str, Any] = {}


def get_generation_config() -> Dict[str, str]:
    primary_label = {
        "openai_compatible": LLM_API_MODEL,
        "ollama": LLM_OLLAMA_MODEL,
        "transformers": LLM_MODEL_PATH or "transformers-local",
    }.get(LLM_BACKEND, "unknown")

    fallback_label = LLM_OLLAMA_MODEL if LLM_BACKEND == "openai_compatible" else ""
    return {
        "backend": LLM_BACKEND,
        "primary_model": primary_label,
        "fallback_model": fallback_label,
    }


def get_last_generation_info() -> Dict[str, Any]:
    return dict(_last_generation_info)


def _set_generation_info(
    active_model: str,
    active_backend: str,
    used_fallback: bool,
    error: str = "",
):
    global _last_generation_info
    config = get_generation_config()
    _last_generation_info = {
        **config,
        "active_model": active_model,
        "active_backend": active_backend,
        "used_fallback": used_fallback,
        "error": error,
    }


def warm_ollama():
    """Warm up Ollama model để tránh cold start (~5-10s)."""
    if LLM_BACKEND != "ollama":
        return
    try:
        logger.info("[LLM] Warming up Ollama model...")
        _generate_ollama("SELECT 1;", max_tokens=8, temperature=0)
        logger.info("[LLM] Ollama warm-up done.")
    except Exception as e:
        logger.warning(f"[LLM] Ollama warm-up failed: {e}")


def warm_openai_compatible():
    """Warm up OpenAI-compatible endpoint de giam cold start."""
    if LLM_BACKEND != "openai_compatible":
        return
    try:
        logger.info("[LLM] Warming up OpenAI-compatible model...")
        _generate_openai_compatible("SELECT 1;", max_tokens=8, temperature=0)
        logger.info("[LLM] OpenAI-compatible warm-up done.")
    except Exception as e:
        logger.warning(f"[LLM] OpenAI-compatible warm-up failed: {e}")


# ════════════════════════════════════════════════════════════
#  OpenAI-compatible Backend
# ════════════════════════════════════════════════════════════

def _generate_openai_compatible(
    prompt: str,
    model: str = LLM_API_MODEL,
    max_tokens: int = LLM_MAX_NEW_TOKENS,
    temperature: float = LLM_TEMPERATURE,
) -> str:
    """Call OpenAI-compatible /v1/chat/completions endpoint."""
    url = f"{LLM_API_BASE_URL.rstrip('/')}/chat/completions"
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
    }
    
    # Only add Authorization if api_key is meaningful (not EMPTY)
    if LLM_API_KEY and LLM_API_KEY != "EMPTY":
        headers["Authorization"] = f"Bearer {LLM_API_KEY}"
    
    req = Request(url, data=payload, headers=headers)

    try:
        with urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            logger.debug(f"[LLM-OpenAI] finish_reason: {body.get('choices', [{}])[0].get('finish_reason')}")
            
            choices = body.get("choices", [])
            if not choices:
                raise RuntimeError(f"No choices returned from API: {body}")
            
            message = choices[0].get("message", {})
            content = message.get("content")
            
            # Prefer content field - don't use reasoning as SQL source
            # (reasoning contains thinking steps, not final SQL)
            if not content or (isinstance(content, str) and content.isspace()):
                # Check if this is just whitespace or truly empty
                finish_reason = choices[0].get("finish_reason")
                logger.warning(f"[LLM-OpenAI] Empty content (finish_reason={finish_reason}). Full message excerpt: {str(message)[:300]}")
                return ""
            
            return str(content).strip()
    
    except URLError as e:
        logger.error(f"[LLM-OpenAI] URLError: {e}")
        raise RuntimeError(
            f"OpenAI-compatible endpoint not reachable at {LLM_API_BASE_URL}. "
            f"Error: {e}"
        )
    except json.JSONDecodeError as e:
        logger.error(f"[LLM-OpenAI] Invalid JSON response: {e}")
        raise RuntimeError(f"OpenAI-compatible API returned invalid JSON: {e}")
    except Exception as e:
        logger.error(f"[LLM-OpenAI] Unexpected error: {e}", exc_info=True)
        raise


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
    Generate SQL tu prompt theo backend trong LLM_BACKEND.
    """
    last_error = ""
    try:
        if LLM_BACKEND == "openai_compatible":
            raw = _generate_openai_compatible(prompt, max_tokens=max_new_tokens, temperature=temperature)
            if raw and raw.strip():
                _set_generation_info(LLM_API_MODEL, "openai_compatible", False)
            else:
                raise RuntimeError("Primary OpenAI-compatible model returned empty response")
        elif LLM_BACKEND == "ollama":
            raw = _generate_ollama(prompt, max_tokens=max_new_tokens, temperature=temperature)
            _set_generation_info(LLM_OLLAMA_MODEL, "ollama", False)
        elif LLM_BACKEND == "transformers":
            raw = _generate_transformers(prompt, max_tokens=max_new_tokens, temperature=temperature)
            _set_generation_info(LLM_MODEL_PATH or "transformers-local", "transformers", False)
        else:
            raise ValueError(f"Unknown LLM_BACKEND: {LLM_BACKEND}")
    except Exception as exc:
        last_error = str(exc)
        if LLM_BACKEND == "openai_compatible":
            logger.warning(f"[LLM] Primary model failed, falling back to Ollama: {exc}")
            raw = _generate_ollama(prompt, max_tokens=max_new_tokens, temperature=temperature)
            _set_generation_info(LLM_OLLAMA_MODEL, "ollama", True, error=last_error)
        else:
            _set_generation_info(get_generation_config()["primary_model"], LLM_BACKEND, False, error=last_error)
            raise

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
    # Handle None/empty response
    if not response:
        logger.warning("[LLM] Empty response from LLM backend")
        return ""
    
    if not isinstance(response, str):
        response = str(response)
    
    # Loại bỏ prompt nếu response chứa cả prompt
    if prompt and isinstance(prompt, str) and response.startswith(prompt):
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
