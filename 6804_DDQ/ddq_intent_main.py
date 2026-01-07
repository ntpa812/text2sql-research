"""Knowledge Base Microservice - FastAPI với Per-Example Embedding"""

# NOTE: Pixeltable uses nest_asyncio internally which causes async warnings on Windows
# These warnings don't affect functionality - all operations complete successfully
# This is a known Pixeltable + uvicorn compatibility issue on Windows
import sys
# sys.path.insert(0, "/home/javis-ai/Javis_AI_UAT/api/Intent_Recognitions_notrain") 
# sys.path.insert(0, "Intent_Recognitions_notrain") 
# sys.path.insert(0, "..") 
import logging

# Suppress asyncio RuntimeError warnings caused by Pixeltable's nest_asyncio on Windows
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

# Also suppress uvicorn error logs for the known nest_asyncio issue
class AsyncioErrorFilter(logging.Filter):
    def filter(self, record):
        # Filter out the specific nest_asyncio related errors
        if 'Non-thread-safe operation' in str(record.getMessage()):
            return False
        return True

# Apply filter to uvicorn loggers
for logger_name in ['uvicorn.error', 'uvicorn.access']:
    uvicorn_logger = logging.getLogger(logger_name)
    uvicorn_logger.addFilter(AsyncioErrorFilter())

from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from difflib import SequenceMatcher
import json
import re
import time
import pandas as pd
import numpy as np

# Clear CUDA cache before loading models (fix meta tensor error)
import torch

from talibs.fixtypo import tafix_tokens
if torch.cuda.is_available():
    torch.cuda.empty_cache()
    print(f"[CUDA] Cleared cache. Device: {torch.cuda.get_device_name(0)}")

import pixeltable as pxt
from pixeltable.functions.huggingface import sentence_transformer
import ddq_intent_config as config
from ddq_intent_config import log_func
from talibs.talibs_words import tokenize_vietnamese_best
from contextlib import asynccontextmanager
from sentence_transformers import SentenceTransformer
import threading
from concurrent.futures import ThreadPoolExecutor
from talibs.nlp import VietnameseTextNormalizer 
from talibs.nlp.unicode_utils import normalize_text, normalize_dict

from tatools01.ParamsBase import TactParameters, pp
AppName="DDQ_dynamic_data_query"
class Params_VietnameseNormalizer(TactParameters):
    """
    Tham số cho Vietnamese Text Normalizer
    Pipeline xử lý: Text Cleaning → Keyboard Typo → Teencode/Abbreviation → Diacritics → Query Rewriting
    """
    def __init__(self):
        super().__init__(ModuleName="VietnameseNormalizer", params_dir='./')
        self.HD = ["Tham số cho module chuẩn hóa văn bản tiếng Việt"]

        # ==== Đường dẫn dictionary files ====
        self.dict_dir = "data_models/nlp_dictionaries"
        self.teencode_dict_path = f"{self.dict_dir}/teencode_dict.json"
        self.banking_abbr_path = f"{self.dict_dir}/banking_abbreviations.json"
        self.keyboard_typo_path = f"{self.dict_dir}/keyboard_typos.json"
        self.stopwords_path = f"{self.dict_dir}/stopwords_vi.json"

        # ==== Stage 1: Text Cleaning ====
        self.enable_text_cleaning = True
        self.remove_emoji = True
        self.normalize_unicode = True  # NFC normalization
        self.normalize_whitespace = True
        self.lowercase = True

        # ==== Stage 2: Keyboard Typo Correction ====
        self.enable_keyboard_typo = True
        self.telex_correction = True  # nhuxng → những, tieenf → tiền
        self.vni_correction = True    # nhu7ng → những

        # ==== Stage 3: Teencode & Abbreviation Expansion ====
        self.enable_teencode_expansion = True
        self.enable_banking_abbreviation = True  # CCTG → chứng chỉ tiền gửi
        self.min_word_length_for_abbr = 2  # Bỏ qua từ ngắn hơn 2 ký tự

        # ==== Stage 4: Diacritics Restoration ====
        self.enable_diacritics_restoration = False  # Tắt mặc định vì cần model
        self.diacritics_model_path = ""  # Path to vn-accent-restorer model
        self.diacritics_confidence_threshold = 0.7

        # ==== Stage 5: Query Rewriting (for RAG) ====
        self.enable_query_rewriting = False  # Tắt mặc định vì cần LLM
        self.query_rewrite_llm_url = "http://192.168.3.7:6801/v1/chat/completions"
        self.query_rewrite_model = "openai/gpt-oss-20b"
        self.query_rewrite_max_tokens = 128

        # ==== Stopwords cho BM25 ====
        self.use_extended_stopwords = True
        self.custom_stopwords = []  # Thêm stopwords tùy chỉnh

        # ==== Semantic Cache (cho Query Rewriting) ====
        self.enable_semantic_cache = False
        self.cache_similarity_threshold = 0.92
        self.cache_max_size = 10000
        self.cache_ttl_hours = 24

        # ==== Logging ====
        self.log_normalized_queries = True
        self.log_level = "INFO"
        
        self.web_title="Dynamic Data Query (DDQ) Intents"
        
        self.load_then_save_to_yaml(file_path=f"{AppName}.yml")

# tmux new     -s  "Intent_DDQ_p_6804"

# Thread pool for running blocking operations
_executor = ThreadPoolExecutor(max_workers=4)

# ========= Config cấp bên ngoài ==============================================
mPs_intent = Params_VietnameseNormalizer()
vietnamese_normalizer = VietnameseTextNormalizer(mPs_intent)

# ============================================================================
# EMBEDDING MODEL - Singleton với GPU/CPU auto-detection
# ============================================================================
_embedding_model = None
_embedding_device = None

def get_embedding_model():
    """
    Lazy-load embedding model với auto GPU/CPU detection.
    Returns: (model, device_name)
    """
    global _embedding_model, _embedding_device

    if _embedding_model is None:
        # Auto-detect device
        if torch.cuda.is_available():
            device = "cuda"
            _embedding_device = f"GPU ({torch.cuda.get_device_name(0)})"
        else:
            device = "cpu"
            _embedding_device = "CPU"

        log_func("get_embedding_model", f"Loading model on {_embedding_device}...", debug_level=1)

        # Load model với device specification
        _embedding_model = SentenceTransformer(
            config.EMBEDDING_MODEL,
            device=device
        )

        log_func("get_embedding_model", f"Model loaded on {_embedding_device}", debug_level=1)

    return _embedding_model, _embedding_device


def encode_query(query_text: str) :
    """
    Encode query text thành embedding vector.
    Sử dụng cached model với GPU nếu có.

    Returns: numpy array embedding vector
    """
    model, device = get_embedding_model()

    # Encode với normalize để dùng cosine similarity
    embedding = model.encode(
        query_text,
        normalize_embeddings=True,
        show_progress_bar=False
    )

    return embedding


# ============================================================================
# EMBEDDINGS CACHE - Pre-computed embeddings cho fast similarity search
# ============================================================================
_embeddings_cache = {
    'examples': None,      # Dict: example_id -> embedding vector
    'examples_meta': None, # DataFrame với doc_id, example_text
    'docs': None,          # Dict: doc_id -> embedding vector
    'docs_meta': None,     # DataFrame với doc info
    'initialized': False
}
_cache_lock = threading.RLock()  # Thread-safe lock for cache operations


def build_embeddings_cache(doc_table, examples_table, force_rebuild: bool = False):
    """
    Pre-compute và cache embeddings cho tất cả examples và documents.
    Chỉ cần chạy 1 lần khi startup hoặc khi data thay đổi.
    Thread-safe với RLock.
    """
    global _embeddings_cache

    # Quick check without lock
    if _embeddings_cache['initialized'] and not force_rebuild:
        return _embeddings_cache

    # Acquire lock for thread-safe cache building
    with _cache_lock:
        # Double-check after acquiring lock
        if _embeddings_cache['initialized'] and not force_rebuild:
            return _embeddings_cache

        log_func("build_embeddings_cache", "Building embeddings cache...", debug_level=1)
        start_time = time.perf_counter()

        model, device = get_embedding_model()

        # 1. Cache examples embeddings
        examples_df = examples_table.select(
            examples_table.doc_id,
            examples_table.example_text,
            examples_table.example_formatted
        ).collect().to_pandas()

        if len(examples_df) > 0:
            # Batch encode tất cả examples
            example_texts = examples_df['example_formatted'].tolist()
            example_embeddings = model.encode(
                example_texts,
                normalize_embeddings=True,
                show_progress_bar=False,
                batch_size=32
            )
            _embeddings_cache['examples'] = example_embeddings
            _embeddings_cache['examples_meta'] = examples_df[['doc_id', 'example_text']].copy()

        # 2. Cache documents embeddings (search_text field)
        docs_df = doc_table.select(
            doc_table.doc_id,
            doc_table.document,
            doc_table.description,
            doc_table.examples_raw,
            doc_table.keyword,
            doc_table.metadata,
            doc_table.search_text
        ).collect().to_pandas()

        if len(docs_df) > 0:
            # Batch encode tất cả search_text
            search_texts = docs_df['search_text'].tolist()
            doc_embeddings = model.encode(
                search_texts,
                normalize_embeddings=True,
                show_progress_bar=False,
                batch_size=32
            )
            _embeddings_cache['docs'] = doc_embeddings
            _embeddings_cache['docs_meta'] = docs_df.copy()

        _embeddings_cache['initialized'] = True

        elapsed = time.perf_counter() - start_time
        log_func("build_embeddings_cache",
                 f"Cache built in {elapsed:.2f}s: {len(examples_df)} examples, {len(docs_df)} docs on {device}",
                 debug_level=1)

        return _embeddings_cache


def invalidate_embeddings_cache():
    """Reset embeddings cache khi data thay đổi. Thread-safe."""
    global _embeddings_cache
    with _cache_lock:
        _embeddings_cache = {
            'examples': None,
            'examples_meta': None,
            'docs': None,
            'docs_meta': None,
            'initialized': False
        }
    log_func("invalidate_embeddings_cache", "Embeddings cache invalidated", debug_level=2)


def compute_similarity_with_cache(query_embedding: np.ndarray, doc_table, examples_table) -> tuple:
    """
    Compute similarity scores sử dụng cached embeddings.
    Chỉ encode query 1 lần, sau đó dùng numpy để tính similarity.
    Thread-safe: copy cache data under lock, compute outside lock.

    Returns: (examples_scores_df, docs_scores_df)
    """
    # Ensure cache is built (this handles its own locking)
    cache = build_embeddings_cache(doc_table, examples_table)

    # Copy cache data under lock to avoid race conditions
    with _cache_lock:
        examples_embeddings = cache['examples'].copy() if cache['examples'] is not None else None
        examples_meta = cache['examples_meta'].copy() if cache['examples_meta'] is not None else None
        docs_embeddings = cache['docs'].copy() if cache['docs'] is not None else None
        docs_meta = cache['docs_meta'].copy() if cache['docs_meta'] is not None else None

    # Reshape query embedding for matrix multiplication
    query_vec = query_embedding.reshape(1, -1)

    # 1. Compute examples similarity (cosine similarity = dot product with normalized vectors)
    examples_scores = None
    if examples_embeddings is not None and examples_meta is not None:
        similarities = np.dot(examples_embeddings, query_vec.T).flatten()
        examples_df = examples_meta
        examples_df['score'] = similarities
        examples_scores = examples_df

    # 2. Compute docs similarity
    docs_scores = None
    if docs_embeddings is not None and docs_meta is not None:
        similarities = np.dot(docs_embeddings, query_vec.T).flatten()
        docs_df = docs_meta
        docs_df['search_score'] = similarities
        docs_scores = docs_df

    return examples_scores, docs_scores

# ============================================================================
# SYSTEM STATUS TRACKING
# ============================================================================
import socket
import os

def _get_server_ip():
    """Lấy IP của server (không phải 127.0.0.1)"""
    try:
        # Tạo socket và connect đến 1 địa chỉ bên ngoài (không gửi data)
        # Điều này giúp lấy được IP thực của máy
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        # Fallback: thử lấy từ hostname
        try:
            hostname = socket.gethostname()
            ip = socket.gethostbyname(hostname)
            if ip.startswith("127."):
                return "localhost"
            return ip
        except Exception:
            return "localhost"

# Server port - có thể được set từ environment hoặc command line
_server_port = int(os.environ.get("PORT", 8000))

_system_status = {
    "ready": False,
    "status": "initializing",
    "message": "Đang khởi tạo hệ thống...",
    "docs_count": 0,
    "examples_count": 0,
    "warmup_time": 0,
    "error": None,
    "server_urls": []
}


def warmup_system():
    """
    Warm-up hệ thống: Load tables, embedding model, chạy dummy query
    Gọi khi server start để đảm bảo mọi thứ sẵn sàng trước khi nhận request
    """
    global _system_status
    import time
    start_time = time.perf_counter()

    try:
        _system_status["status"] = "loading_tables"
        _system_status["message"] = "Đang kết nối database..."
        log_func("warmup", "Loading tables...", debug_level=1)

        # Step 1: Load tables
        doc_table, examples_table = get_tables()

        _system_status["docs_count"] = doc_table.count()
        _system_status["examples_count"] = examples_table.count()
        log_func("warmup", f"Tables loaded: {_system_status['docs_count']} docs, {_system_status['examples_count']} examples", debug_level=1)

        # Step 2: Load embedding model (auto GPU/CPU detection)
        _system_status["status"] = "loading_model"
        _system_status["message"] = "Đang tải model embedding..."
        log_func("warmup", "Loading embedding model...", debug_level=1)

        model, device = get_embedding_model()
        log_func("warmup", f"Embedding model loaded on {device}", debug_level=1)

        # Step 3: Build embeddings cache (pre-compute all embeddings)
        _system_status["status"] = "building_embeddings_cache"
        _system_status["message"] = "Đang pre-compute embeddings..."
        log_func("warmup", "Building embeddings cache...", debug_level=1)

        build_embeddings_cache(doc_table, examples_table)
        log_func("warmup", "Embeddings cache built", debug_level=1)

        # Step 4: Build corpus stats cache
        _system_status["status"] = "building_cache"
        _system_status["message"] = "Đang xây dựng BM25 cache..."
        log_func("warmup", "Building corpus stats cache...", debug_level=1)

        _ = get_corpus_stats(doc_table, examples_table)
        log_func("warmup", "Corpus stats cache built", debug_level=1)

        # Done!
        warmup_time = time.perf_counter() - start_time
        _system_status["ready"] = True
        _system_status["status"] = "ready"
        _system_status["message"] = f"Hệ thống sẵn sàng! ({warmup_time:.1f}s)"
        _system_status["warmup_time"] = round(warmup_time, 2)
        _system_status["error"] = None

        # Build server URLs
        server_ip = _get_server_ip()
        _system_status["server_urls"] = [
            f"http://localhost:{_server_port}",
            f"http://{server_ip}:{_server_port}"
        ]

        log_func("warmup", f"System ready in {warmup_time:.2f}s | URLs: {_system_status['server_urls']}", debug_level=1)

    except Exception as e:
        _system_status["ready"] = False
        _system_status["status"] = "error"
        _system_status["message"] = f"Lỗi khởi tạo: {str(e)}"
        _system_status["error"] = str(e)
        log_func("warmup", f"ERROR during warmup: {e}", debug_level=0)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager - chạy warmup khi server start"""
    log_func("lifespan", "Server starting - running warmup...", debug_level=1)
    warmup_system()
    yield
    log_func("lifespan", "Server shutting down", debug_level=1)


app = FastAPI(title=mPs_intent.web_title, version="2.0.0", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")

log_func("main", "FastAPI app initialized (Per-Example Embedding Architecture)", debug_level=1)

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    """Giao diện web"""
    log_func("index", "Serving web UI", debug_level=2)
    return templates.TemplateResponse("index.html", {"request": request, "web_title": mPs_intent.web_title})


@app.get("/api/status")
def get_system_status():
    """
    Lấy trạng thái hệ thống.
    Frontend gọi endpoint này để biết hệ thống đã sẵn sàng chưa.
    """
    return _system_status


@app.get("/health")
def health_check():
    """
    Simple health check - không phụ thuộc database hay cache.
    Dùng để kiểm tra server còn phản hồi không.
    """
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "message": "Server is alive"
    }


@app.post("/api/rebuild-cache")
def rebuild_cache():
    """
    Force rebuild tất cả caches sau khi data thay đổi.
    Gọi endpoint này sau khi edit document trong DB Manager.

    Sẽ rebuild:
    1. Embeddings cache (in-memory vectors)
    2. Corpus stats cache (BM25 index)
    """
    import time
    start_time = time.perf_counter()

    log_func("rebuild_cache", "Force rebuilding all caches...", debug_level=1)

    # Reset all caches
    reset_all_caches()

    # Get tables
    doc_table, examples_table = get_tables()

    # Force rebuild embeddings cache
    build_embeddings_cache(doc_table, examples_table, force_rebuild=True)

    # Force rebuild corpus stats
    global _corpus_stats_cache, _corpus_stats_doc_count
    _corpus_stats_cache = None
    _corpus_stats_doc_count = None
    get_corpus_stats(doc_table, examples_table)

    elapsed = time.perf_counter() - start_time

    # Get counts for response
    doc_count = len(doc_table.select().collect().to_pandas())
    examples_count = len(examples_table.select().collect().to_pandas())

    log_func("rebuild_cache", f"Cache rebuilt in {elapsed:.2f}s", debug_level=1)

    return {
        "status": "success",
        "message": f"All caches rebuilt in {elapsed:.2f}s",
        "docs_count": doc_count,
        "examples_count": examples_count,
        "rebuild_time": round(elapsed, 2)
    }


@app.get("/api/diagnostics")
def get_diagnostics():
    """
    Chi tiết diagnostics để debug server issues.
    Kiểm tra thread pool, locks, cache status.
    """
    import threading

    diagnostics = {
        "timestamp": datetime.now().isoformat(),
        "thread_info": {
            "active_threads": threading.active_count(),
            "current_thread": threading.current_thread().name,
            "thread_names": [t.name for t in threading.enumerate()]
        },
        "executor_info": {
            "max_workers": _executor._max_workers,
            # ThreadPoolExecutor doesn't expose pending count directly
            "shutdown": _executor._shutdown,
        },
        "cache_status": {
            "embeddings_initialized": _embeddings_cache.get('initialized', False),
            "corpus_stats_cached": _corpus_stats_cache is not None,
        },
        "system_status": _system_status.copy(),
        "lock_info": {}
    }

    # Try to check if we can acquire lock (non-blocking test)
    lock_test = _cache_lock.acquire(blocking=False)
    if lock_test:
        _cache_lock.release()
        diagnostics["lock_info"]["can_acquire_cache_lock"] = True
    else:
        diagnostics["lock_info"]["can_acquire_cache_lock"] = False
        diagnostics["lock_info"]["warning"] = "Cache lock is held by another thread!"

    return diagnostics


# Pydantic models
class Document(BaseModel):
    document: str
    metadata: Optional[dict] = None
    description: Optional[str] = None
    examples: Optional[str] = None
    keyword: Optional[str] = None

class SearchQuery(BaseModel):
    query: str
    top_k: int = config.DEFAULT_TOP_K


# =====================================================================
class inputIntentRecognition(BaseModel):  
    question: str = ""
    
class outputIntentRecognition(BaseModel):
    status: int=0
    groupIntent: str = ""
    intent: str = "" 
    options: List[dict] = []
    score: float=0.0
    question: str = ""




# ============================================================================
# TEXT PROCESSING FUNCTIONS
# ============================================================================

def build_search_text(doc: str, desc: str = "", keyword: str = "") -> str:
    """Tạo search_text từ document + description + keyword (KHÔNG bao gồm examples)"""
    parts = [doc or ""]
    if desc: parts.append(desc)
    if keyword: parts.append(keyword)
    result = " | ".join(parts)
    result = f"passage: {result}"
    log_func("build_search_text", f"Built search_text ({len(result)} chars)", debug_level=3)
    return result


def parse_examples_to_list(examples: str) -> List[str]:
    """Tách chuỗi examples thành danh sách các câu hỏi riêng lẻ"""
    if not examples or not examples.strip():
        return []

    result = []

    # Tách theo dấu ngoặc kép trước
    quoted = re.findall(r'"([^"]+)"', examples)
    if quoted:
        result = [q.strip() for q in quoted if q.strip() and len(q.strip()) > 5]
    else:
        # Tách theo dòng
        lines = re.split(r'[\n]', examples)
        for line in lines:
            cleaned = re.sub(r'^[\s\d\.\)\-\*•🧠]+', '', line)
            cleaned = re.sub(r'^(Ví dụ|Câu hỏi|Example).*?:', '', cleaned, flags=re.IGNORECASE)
            cleaned = cleaned.strip()
            if cleaned and len(cleaned) > 5:
                result.append(cleaned)
    log_func("parse_examples_to_list", f"Parsed {len(result)} examples", debug_level=3)
    return result


def normalize_query(query: str) -> str:
    """Chuẩn hóa query về dạng chuẩn trước khi search

    Steps:
    1. Lowercase và xóa punctuation cuối
    2. Vietnamese diacritics (tai khoan -> tài khoản, ngan hang -> ngân hàng)
    3. Expand abbreviations (tk -> tài khoản, gd -> giao dịch)
    4. Normalize variations (balance -> số dư, saving -> tiết kiệm)
    5. Remove filler words (ơi, ê, hey, yo, bro, real quick, asap)
    6. Clean up whitespace

    Returns:
        Normalized query string
    """
    if not query:
        return ""

    original = query
    query = query.strip().lower()
    query = re.sub(r'[?!.,;:]+$', '', query)

    # Step 1: Vietnamese diacritics normalization (MUST run FIRST)
    # Convert Vietnamese without diacritics to standard form
    # for pattern, replacement in config.VIETNAMESE_DIACRITICS.items():
    #     query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)

    # # Step 2: Expand abbreviations
    # for pattern, replacement in config.ABBREVIATION_EXPANSIONS.items():
    #     query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)

    # # Step 3: Normalize variations to standard form
    # for pattern, replacement in config.VARIATION_NORMALIZATIONS.items():
    #     query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)

    
    # # Step 4: Remove filler words
    # for filler in config.FILLER_WORDS:
    #     # Use word boundary to avoid partial matches
    #     pattern = r'\b' + re.escape(filler) + r'\b'
    #     query = re.sub(pattern, '', query, flags=re.IGNORECASE)

    # Step 5: Clean up whitespace
    query = re.sub(r'\s+', ' ', query).strip()

    # Capitalize first letter
    if query:
        query = query[0].upper() + query[1:] if len(query) > 1 else query.upper()

    log_func("normalize_query", f"'{original[:40]}...' -> '{query[:40]}...'", debug_level=3)
    return query


def format_query_for_search(query: str) -> str:
    """Format query với prefix query: cho E5 model

    Applies normalization first, then adds E5 prefix
    """
    normalized = normalize_query(query)
    return f"query: {normalized}"


def calculate_API_similarity(text1: str, text2: str) -> float:
    """Tính độ tương đồng string (0-100%)"""
    if not text1 or not text2:
        return 0.0
    return SequenceMatcher(None, text1.lower(), text2.lower()).ratio() * 100


def calculate_document_similarity(
    new_doc: dict,
    existing_doc: dict,
    weights: dict | None = None
) -> float:
    """
    Tính độ tương đồng tổng hợp giữa 2 document.

    Trọng số mặc định:
    - document (tên API): 50% - quan trọng nhất
    - keyword: 30% - từ khóa giống nhau = chức năng tương tự
    - examples: 20% - câu hỏi mẫu giống nhau

    Returns: 0-100 (%)
    """
    if weights is None:
        weights = {
            'document': 0.50,
            'keyword': 0.30,
            'examples': 0.20
        }

    total_score = 0.0

    # 1. So sánh document name (tên API)
    doc1 = str(new_doc.get('document', '')).strip().lower()
    doc2 = str(existing_doc.get('document', '')).strip().lower()
    if doc1 and doc2:
        doc_sim = SequenceMatcher(None, doc1, doc2).ratio() * 100
        total_score += doc_sim * weights.get('document', 0.5)

    # 2. So sánh keywords (tách thành set và tính Jaccard)
    kw1 = set(k.strip().lower() for k in str(new_doc.get('keyword', '')).split(',') if k.strip())
    kw2 = set(k.strip().lower() for k in str(existing_doc.get('keyword', '')).split(',') if k.strip())
    if kw1 and kw2:
        intersection = len(kw1 & kw2)
        union = len(kw1 | kw2)
        kw_sim = (intersection / union * 100) if union > 0 else 0
        total_score += kw_sim * weights.get('keyword', 0.3)

    # 3. So sánh examples (tách thành các câu và tính overlap)
    ex1_raw = str(new_doc.get('examples', '') or new_doc.get('examples_raw', ''))
    ex2_raw = str(existing_doc.get('examples', '') or existing_doc.get('examples_raw', ''))
    ex1 = set(e.strip().lower() for e in ex1_raw.split('|') if e.strip())
    ex2 = set(e.strip().lower() for e in ex2_raw.split('|') if e.strip())
    if ex1 and ex2:
        # Tính similarity dựa trên số câu giống nhau
        intersection = len(ex1 & ex2)
        union = len(ex1 | ex2)
        ex_sim = (intersection / union * 100) if union > 0 else 0
        total_score += ex_sim * weights.get('examples', 0.2)

    return round(total_score, 1)


# ============================================================================
# HYBRID SEARCH COMPONENTS (Expert-level accuracy improvement)
# ============================================================================

def tokenize_vietnamese(text: str) -> List[str]:
    return tokenize_vietnamese_best(text=text)

# def tokenize_vietnamese(text: str) -> List[str]:
#     """Tokenize Vietnamese text - simple word-based tokenization

#     For production, consider using underthesea or pyvi for better Vietnamese tokenization
#     """
#     if not text:
#         return []
#     # Lowercase and remove punctuation
#     text = text.lower()
#     text = re.sub(r'[^\w\s]', ' ', text)
#     # Split by whitespace
#     tokens = text.split()
#     # Remove very short tokens
#     return [t for t in tokens if len(t) > 1]




def calculate_bm25_score(   query_tokens: List[str], doc_tokens: List[str],
                            avg_doc_len: float, total_docs: int,
                            doc_freqs: dict) -> float:
    """Calculate BM25 score for a document

    BM25 is a bag-of-words retrieval function that ranks documents based on
    query terms appearing in each document, regardless of their proximity.

    Args:
        query_tokens: Tokenized query
        doc_tokens: Tokenized document
        avg_doc_len: Average document length in corpus
        total_docs: Total number of documents
        doc_freqs: Dictionary mapping terms to document frequencies

    Returns:
        BM25 score (higher is better)
    """
    if not query_tokens or not doc_tokens:
        return 0.0

    k1 = config.BM25_K1
    b = config.BM25_B

    doc_len = len(doc_tokens)
    score = 0.0

    # Count term frequencies in document
    doc_tf = {}
    for token in doc_tokens:
        doc_tf[token] = doc_tf.get(token, 0) + 1

    for term in query_tokens:
        if term not in doc_tf:
            continue

        tf = doc_tf[term]
        df = doc_freqs.get(term, 1)  # Document frequency

        # Cap df at total_docs to prevent edge cases
        df = min(df, total_docs)

        # IDF component (BM25+ variant - always non-negative)
        # Standard: log((N - n + 0.5) / (n + 0.5))
        # BM25+: max(0, log(...)) to ensure non-negative scores
        idf_raw = (total_docs - df + 0.5) / (df + 0.5)
        idf = max(0, np.log(idf_raw + 1))

        # TF component with length normalization
        tf_component = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_doc_len))

        score += idf * tf_component

    return score


def parse_document_keywords(keyword_field: str) -> List[str]:
    """Parse keywords from document's keyword field

    Supports multiple formats:
    - Comma separated: "số dư, balance, tiền trong"
    - Pipe separated: "số dư | balance | tiền trong"
    - Newline separated
    - Mixed

    Returns:
        List of keywords (lowercase, stripped)
    """
    if not keyword_field or not keyword_field.strip():
        return []

    # Split by common separators
    keywords = re.split(r'[,|\n]', keyword_field)
    result = []
    for kw in keywords:
        kw = kw.strip().lower()
        if kw and len(kw) > 1:
            result.append(kw)

    return result


def get_keyword_boost(query: str, document_name: str, document_keywords: str = "") -> float:
    """Calculate keyword boost score based on document's keywords field

    If query contains keywords defined in the document's keyword field,
    boost the score for that document.

    Args:
        query: User's search query (normalized)
        document_name: Name of the document
        document_keywords: Keywords from document's keyword field

    Returns:
        Boost score (0.0 to 1.0)
    """
    query_lower = query.lower()

    # Parse keywords from document's keyword field
    keywords = parse_document_keywords(document_keywords)

    if not keywords:
        return 0.0

    # Count how many keywords appear in query
    matched_keywords = []
    for kw in keywords:
        if kw in query_lower:
            matched_keywords.append(kw)

    if not matched_keywords:
        return 0.0

    # Calculate boost based on number of matches
    # More matches = higher confidence = higher boost
    boost = min(len(matched_keywords) * 0.25, 1.0)  # Cap at 1.0

    log_func("get_keyword_boost",
             f"Query: '{query[:30]}...' | Doc: {document_name[:20]} | Boost: {boost:.2f} | Matched: {matched_keywords[:3]}",
             debug_level=3)

    return boost


def classify_query_intent_from_docs(query: str, doc_keywords_map: dict) -> Optional[str]:
    """Pre-classify query intent based on document keywords

    Uses keywords from each document's keyword field to classify.

    Args:
        query: User's search query (normalized)
        doc_keywords_map: Dict mapping doc_id -> (document_name, keywords_string)

    Returns:
        Best matching document name or None if ambiguous
    """
    query_lower = query.lower()
    doc_scores = {}

    for doc_id, (doc_name, keywords_str) in doc_keywords_map.items():
        keywords = parse_document_keywords(keywords_str)
        score = 0
        for kw in keywords:
            if kw in query_lower:
                score += 1
        if score > 0:
            doc_scores[doc_name] = score

    if not doc_scores:
        log_func("classify_query_intent", f"No keyword matches found in: '{query[:50]}'", debug_level=2)
        return None

    # Get the document with highest score
    best_doc = max(doc_scores, key=lambda x: doc_scores[x])
    best_score = doc_scores[best_doc]

    # Check if there's a clear winner
    sorted_scores = sorted(doc_scores.values(), reverse=True)
    second_best = sorted_scores[1] if len(sorted_scores) > 1 else 0

    if best_score >= 1 and best_score > second_best:
        log_func("classify_query_intent",
                 f"Classified: '{query[:30]}...' -> {best_doc[:30]} (score={best_score})",
                 debug_level=2)
        return best_doc

    log_func("classify_query_intent",
             f"Ambiguous: '{query[:30]}...' | Scores: {doc_scores}",
             debug_level=2)
    return None


def build_corpus_stats(doc_table, examples_table) -> dict:
    """Build corpus statistics for BM25 scoring

    Returns dict with:
        - doc_tokens: {doc_id: [tokens]}
        - example_tokens: {doc_id: [all example tokens]}
        - avg_doc_len: average document length
        - doc_freqs: {term: document_frequency}
        - total_docs: total number of documents
    """
    docs_df = doc_table.select(
        doc_table.doc_id,
        doc_table.document,
        doc_table.description,
        doc_table.keyword
    ).collect().to_pandas()

    examples_df = examples_table.select(
        examples_table.doc_id,
        examples_table.example_text
    ).collect().to_pandas()

    doc_tokens = {}
    example_tokens = {}
    all_tokens = []
    doc_freqs = {}

    for _, row in docs_df.iterrows():
        doc_id = row['doc_id']
        # Combine document fields
        text = f"{row['document']} {row['description']} {row['keyword']}"
        tokens = tokenize_vietnamese(text)
        doc_tokens[doc_id] = tokens
        all_tokens.extend(tokens)

        # Track document frequencies
        unique_terms = set(tokens)
        for term in unique_terms:
            doc_freqs[term] = doc_freqs.get(term, 0) + 1

    # Group examples by doc_id
    # NOTE: KHÔNG thêm example terms vào doc_freqs
    # Vì doc_freqs chỉ nên đếm số documents chứa term, không đếm examples
    for doc_id in docs_df['doc_id'].unique():
        doc_examples = examples_df[examples_df['doc_id'] == doc_id]
        tokens = []
        for _, ex_row in doc_examples.iterrows():
            tokens.extend(tokenize_vietnamese(ex_row['example_text']))
        example_tokens[doc_id] = tokens
        # REMOVED: Don't add to doc_freqs from examples (was causing df > total_docs)

    total_docs = len(docs_df)
    avg_doc_len = len(all_tokens) / total_docs if total_docs > 0 else 1

    return {
        'doc_tokens': doc_tokens,
        'example_tokens': example_tokens,
        'avg_doc_len': avg_doc_len,
        'doc_freqs': doc_freqs,
        'total_docs': total_docs
    }


# Cache for corpus stats (rebuilt when documents change)
_corpus_stats_cache = None
_corpus_stats_doc_count = None


def get_corpus_stats(doc_table, examples_table) -> dict:
    """Get cached corpus statistics"""
    global _corpus_stats_cache, _corpus_stats_doc_count

    current_count = len(doc_table.select().collect().to_pandas())

    if _corpus_stats_cache is None or _corpus_stats_doc_count != current_count:
        log_func("get_corpus_stats", "Rebuilding corpus stats cache...", debug_level=1)
        _corpus_stats_cache = build_corpus_stats(doc_table, examples_table)
        _corpus_stats_doc_count = current_count

    return _corpus_stats_cache


def reset_corpus_stats_cache():
    """Reset corpus stats cache when documents change"""
    global _corpus_stats_cache, _corpus_stats_doc_count
    _corpus_stats_cache = None
    _corpus_stats_doc_count = None


def reset_all_caches():
    """Reset tất cả caches khi data thay đổi"""
    reset_corpus_stats_cache()
    invalidate_embeddings_cache()
    log_func("reset_all_caches", "All caches invalidated", debug_level=2)


def perform_hybrid_search(query_text: str, doc_table, examples_table, top_k: int) -> List[dict]:
    """Perform hybrid search combining Semantic + BM25 + Keyword Boosting

    OPTIMIZED VERSION: Uses cached embeddings + single query encoding
    - Query encoded only ONCE (saves ~500ms on CPU)
    - Similarity computed via numpy dot product (instant)
    - Auto GPU/CPU detection

    Args:
        query_text: Raw query text
        doc_table: Pixeltable documents table
        examples_table: Pixeltable examples table
        top_k: Number of results to return

    Returns:
        List of result dictionaries
    """
    t={}
    t[1]= time.perf_counter()
    normalized_query = normalize_query(query_text)
    formatted_query = normalized_query
    log_func("perform_hybrid_search", f"query_text: [{query_text}] - formatted_query: [{formatted_query}] - normalized_query: [{normalized_query}]", debug_level=3)

    t[2]= time.perf_counter()

    # Step 1: Encode query ONCE (this is the expensive operation)
    query_embedding = encode_query(formatted_query)

    t[3]= time.perf_counter()

    # Step 2: Compute similarity với cached embeddings (instant với numpy)
    examples_df, docs_df = compute_similarity_with_cache(query_embedding, doc_table, examples_table)

    if examples_df is None or len(examples_df) == 0:
        print("examples_df=[]")
        return []

    t[4]= time.perf_counter()

    # Step 3: Group by doc_id, lấy MAX score
    max_example_scores = examples_df.groupby('doc_id').agg({
        'score': 'max',
        'example_text': 'first'
    }).reset_index()
    max_example_scores.columns = ['doc_id', 'max_example_score', 'best_example']

    t[5]= time.perf_counter()
    # Step 4: Merge semantic scores
    merged = docs_df.merge(max_example_scores, on='doc_id', how='left')
    merged['max_example_score'] = merged['max_example_score'].fillna(0)

    # Combined semantic score
    merged['semantic_score'] = (
        merged['max_example_score'] * config.EXAMPLES_WEIGHT +
        merged['search_score'] * config.SEARCH_TEXT_WEIGHT
    )
    t[6]= time.perf_counter()
    # Step 5: BM25 scoring
    corpus_stats = get_corpus_stats(doc_table, examples_table)
    query_tokens = tokenize_vietnamese(normalized_query)
    t[7]= time.perf_counter()
    bm25_scores = []
    for _, row in merged.iterrows():
        doc_id = row['doc_id']
        all_tokens = corpus_stats['doc_tokens'].get(doc_id, []) + \
                     corpus_stats['example_tokens'].get(doc_id, [])

        bm25 = calculate_bm25_score(
            query_tokens,
            all_tokens,
            corpus_stats['avg_doc_len'],
            corpus_stats['total_docs'],
            corpus_stats['doc_freqs']
        )
        bm25_scores.append(bm25)

    merged['bm25_score'] = bm25_scores

    
    # Log BM25 stats for debugging
    min_bm25 = merged['bm25_score'].min()
    max_bm25_raw = merged['bm25_score'].max()
    log_func("perform_hybrid_search",
             f"BM25 raw scores: min={min_bm25:.4f}, max={max_bm25_raw:.4f}",
             debug_level=3)

    # Normalize BM25 scores to [0, 1]
    max_bm25 = max(max_bm25_raw, 0.001)
    merged['bm25_normalized'] = merged['bm25_score'] / max_bm25
    t[8]= time.perf_counter()
    
    # Step 6: Keyword Boosting (using document's keyword field)
    keyword_boosts = []
    for _, row in merged.iterrows():
        doc_keywords = str(row.get('keyword', '') or '')
        boost = get_keyword_boost(normalized_query, row['document'], doc_keywords)
        keyword_boosts.append(boost)
    merged['keyword_boost'] = keyword_boosts

    t[9]= time.perf_counter()
    # Step 7: Query Classification (for logging/output)
    doc_keywords_map = {
        row['doc_id']: (row['document'], str(row.get('keyword', '') or ''))
        for _, row in merged.iterrows()
    }
    classified_intent = classify_query_intent_from_docs(normalized_query, doc_keywords_map)

    t[10]= time.perf_counter()
    # Step 8: Calculate FINAL HYBRID SCORE
    merged['score'] = (
        merged['semantic_score'] * config.SEMANTIC_WEIGHT +
        merged['bm25_normalized'] * config.BM25_WEIGHT +
        merged['keyword_boost'] * config.KEYWORD_BOOST_WEIGHT
    )
    t[11]= time.perf_counter()
    # Sort và lấy top_k
    merged = merged.sort_values('score', ascending=False).head(top_k)

    # Format output
    results = []
    for _, row in merged.iterrows():
        results.append({
            'document': row['document'],
            'metadata': row['metadata'],
            'description': row['description'],
            'examples': row['examples_raw'],
            'keyword': row['keyword'],
            'score': round(float(row['score']), 4),
            'score_semantic': round(float(row['semantic_score']), 4),
            'score_max_example': round(float(row['max_example_score']), 4),
            'score_search_text': round(float(row['search_score']), 4),
            'score_bm25': round(float(row['bm25_normalized']), 4),
            'score_keyword_boost': round(float(row['keyword_boost']), 4),
            'best_matching_example': row.get('best_example', ''),
            'classified_intent': classified_intent
        })
    t[12]= time.perf_counter()
    # keys = sorted(t.keys())
    # for k1, k2 in zip(keys, keys[1:]):
    #     dt = t[k2] - t[k1]
    #     print(f"{k1} → {k2}: {dt*1000:>12.3f} miliseconds")
    # print(f'total: {(t[12]-t[1])*1000:>12.3f} miliseconds')
    return results


# ============================================================================
# DATABASE MANAGEMENT
# ============================================================================

_cached_doc_table = None
_cached_examples_table = None


def _create_tables_internal():
    """Internal: Tạo tables và indexes (không drop)

    Chỉ được gọi khi tables chưa tồn tại.
    """
    log_func("_create_tables_internal", "Creating new tables...", debug_level=1)

    # Ensure directory exists
    try:
        pxt.create_dir(config.DB_DIR)
    except Exception as e:
        log_func("_create_tables_internal", f"Dir already exists or error: {e}", debug_level=2)

    # Table 1: Documents
    doc_table = pxt.create_table(config.DB_TABLE, {
        "doc_id": pxt.Int,
        "document": pxt.String,
        "metadata": pxt.Json,
        "description": pxt.String,
        "examples_raw": pxt.String,
        "keyword": pxt.String,
        "search_text": pxt.String,
        "similarity_score": pxt.Float,
        "duplicate_with_id": pxt.Int,
        "duplicate_with_name": pxt.String
    })
    log_func("_create_tables_internal", "Documents table created", debug_level=2)

    # Table 2: Examples (MỖI CÂU HỎI 1 ROW)
    examples_table = pxt.create_table(config.EXAMPLES_TABLE, {
        "doc_id": pxt.Int,
        "example_text": pxt.String,
        "example_formatted": pxt.String,
    })
    log_func("_create_tables_internal", "Examples table created", debug_level=2)

    # Add embedding indexes
    embed_model = sentence_transformer.using(model_id=config.EMBEDDING_MODEL)

    doc_table.add_embedding_index(column='search_text', idx_name='search_embed', string_embed=embed_model)
    log_func("_create_tables_internal", "search_embed index added", debug_level=2)

    examples_table.add_embedding_index(column='example_formatted', idx_name='example_embed', string_embed=embed_model)
    log_func("_create_tables_internal", "example_embed index added", debug_level=2)

    log_func("_create_tables_internal", f"All indexes created with model: {config.EMBEDDING_MODEL}", debug_level=1)
    return doc_table, examples_table


def drop_and_create_tables():
    """XÓA TẤT CẢ DỮ LIỆU và tạo tables mới

    CHỈ DÙNG KHI USER YÊU CẦU XÓA TẤT CẢ (delete_all_documents)
    """
    global _cached_doc_table, _cached_examples_table
    _cached_doc_table = None
    _cached_examples_table = None

    log_func("drop_and_create_tables", "⚠️ DROPPING ALL DATA...", debug_level=0)
    pxt.drop_dir(config.DB_DIR, force=True)

    return _create_tables_internal()


def create_tables():
    """Tạo tables nếu chưa tồn tại, KHÔNG xóa dữ liệu

    Backward compatible - gọi từ các nơi khác nhưng AN TOÀN
    """
    global _cached_doc_table, _cached_examples_table

    # Kiểm tra tables đã tồn tại chưa
    try:
        doc_table = pxt.get_table(config.DB_TABLE)
        examples_table = pxt.get_table(config.EXAMPLES_TABLE)
        log_func("create_tables", "Tables already exist, returning existing", debug_level=2)
        _cached_doc_table = doc_table
        _cached_examples_table = examples_table
        return doc_table, examples_table
    except Exception as e:
        log_func("create_tables", f"Tables don't exist, creating new: {e}", debug_level=2)
        _cached_doc_table = None
        _cached_examples_table = None
        doc_table, examples_table = _create_tables_internal()
        _cached_doc_table = doc_table
        _cached_examples_table = examples_table
        return doc_table, examples_table


def validate_tables() -> bool:
    """Kiểm tra cả 2 tables có đúng schema không"""
    try:
        doc_table = pxt.get_table(config.DB_TABLE)
        examples_table = pxt.get_table(config.EXAMPLES_TABLE)

        doc_df = doc_table.select().limit(1).collect().to_pandas()
        if 'doc_id' not in doc_df.columns:
            log_func("validate_tables", "doc_id column missing in documents", debug_level=1)
            return False

        ex_df = examples_table.select().limit(1).collect().to_pandas()
        if 'doc_id' not in ex_df.columns:
            log_func("validate_tables", "doc_id column missing in examples", debug_level=1)
            return False

        log_func("validate_tables", "Tables validated OK", debug_level=2)
        return True
    except Exception as e:
        log_func("validate_tables", f"Validation failed: {e}", debug_level=1)
        return False


def get_tables(force_check: bool = False):
    """Lấy cả 2 tables - AN TOÀN, không xóa dữ liệu"""
    global _cached_doc_table, _cached_examples_table
    log_func("get_tables", "Getting tables...", debug_level=2)

    # Trả cache nếu có
    if _cached_doc_table is not None and _cached_examples_table is not None and not force_check:
        log_func("get_tables", "Returning cached tables", debug_level=2)
        return _cached_doc_table, _cached_examples_table

    # Try to get existing tables first
    try:
        _cached_doc_table = pxt.get_table(config.DB_TABLE)
        _cached_examples_table = pxt.get_table(config.EXAMPLES_TABLE)
        log_func("get_tables", "Loaded existing tables", debug_level=2)
        return _cached_doc_table, _cached_examples_table
    except Exception as e:
        error_str = str(e).lower()
        # Chỉ tạo mới nếu tables THỰC SỰ không tồn tại
        # Các lỗi khác (GPU, model loading) phải raise lên
        if "does not exist" in error_str or "not found" in error_str or "no such" in error_str:
            log_func("get_tables", f"Tables not found, creating new: {e}", debug_level=1)
            _cached_doc_table, _cached_examples_table = _create_tables_internal()
            return _cached_doc_table, _cached_examples_table
        else:
            # Lỗi khác (GPU memory, model loading, etc.) - raise lên
            log_func("get_tables", f"ERROR loading tables (NOT 'not found'): {e}", debug_level=0)
            raise


def get_table(force_check: bool = False):
    """Backward compatible - trả về documents table"""
    doc_table, _ = get_tables(force_check)
    return doc_table


def reset_table_cache():
    """Reset cache"""
    global _cached_doc_table, _cached_examples_table
    _cached_doc_table = None
    _cached_examples_table = None


def get_next_doc_id(doc_table) -> int:
    """Lấy doc_id tiếp theo"""
    try:
        df = doc_table.select(doc_table.doc_id).collect().to_pandas()
        if len(df) == 0:
            return 0
        return int(df['doc_id'].max()) + 1
    except:
        return 0


def insert_document_with_examples(doc_table, examples_table, doc_data: dict, doc_id: int) -> int:
    """Insert 1 document và các examples của nó"""
    examples_raw = str(doc_data.get('examples', '') or '')

    search_text_value = build_search_text(
        str(doc_data.get('document', '')),
        str(doc_data.get('description', '')),
        str(doc_data.get('keyword', ''))
    )
    
    doc_record = {
        'doc_id': doc_id,
        'document': doc_data.get('document', ''),
        'metadata': doc_data.get('metadata', {}),
        'description': doc_data.get('description', ''),
        'examples_raw': examples_raw,
        'keyword': doc_data.get('keyword', ''),
        'search_text': search_text_value,
        'similarity_score': doc_data.get('similarity_score', 0.0),
        'duplicate_with_id': doc_data.get('duplicate_with_id'),
        'duplicate_with_name': doc_data.get('duplicate_with_name', '')
    }
    
    log_func("insert_document_with_examples", f"Inserting doc_id={doc_id}, search_text length={len(search_text_value)}", debug_level=2)
    
    try:
        import time
        start_time = time.perf_counter()
        log_func("insert_document_with_examples", f"Starting doc_table.insert() for doc_id={doc_id}...", debug_level=1)
        
        doc_table.insert([doc_record])
        
        insert_time = time.perf_counter() - start_time
        log_func("insert_document_with_examples", f"doc_table.insert() completed in {insert_time:.2f}s for doc_id={doc_id}", debug_level=1)
    except Exception as e:
        log_func("insert_document_with_examples", f"ERROR inserting doc_id={doc_id}: {type(e).__name__}: {e}", debug_level=0)
        raise
    # Parse và insert từng example
    example_list = parse_examples_to_list(examples_raw)
    if example_list:
        example_records = [{
            'doc_id': doc_id,
            'example_text': ex_text,
            'example_formatted': f"passage: {ex_text}"
        } for ex_text in example_list]
        examples_table.insert(example_records)
        log_func("insert_document_with_examples", f"Inserted {len(example_records)} examples for doc_id={doc_id}", debug_level=3)
    print("example_list = parse_examples_to_list(examples_raw) Done")
    return len(example_list)


# ============================================================================
# CRUD ENDPOINTS
# ============================================================================

def _list_documents_sync():
    """Synchronous helper for list_documents"""
    doc_table, _ = get_tables()
    docs = doc_table.select().collect().to_pandas()

    # Rename examples_raw -> examples for backward compatibility
    if 'examples_raw' in docs.columns:
        docs = docs.rename(columns={'examples_raw': 'examples'})

    # Convert NaN to None và numpy types to Python native types
    docs = docs.fillna('')
    result = docs.to_dict(orient='records')

    # Ensure all values are JSON serializable
    for row in result:
        for key, val in row.items():
            if hasattr(val, 'item'):  # numpy scalar
                row[key] = val.item()
            elif val != val:  # NaN check
                row[key] = None

    return result


@app.get("/documents")
def list_documents():
    """Xem tất cả documents"""
    log_func("list_documents", "Fetching all documents...", debug_level=2)
    result = _list_documents_sync()
    log_func("list_documents", f"Found {len(result)} documents", debug_level=1)
    return result


@app.post("/documents")
def add_document(doc: Document):
    """Thêm document mới"""
    log_func("add_document", f"Adding document: {doc.document[:50]}...", debug_level=1)
    doc_table, examples_table = get_tables()

    # Lấy next doc_id
    doc_id = get_next_doc_id(doc_table)

    # Tính similarity với existing documents (dùng nhiều trường)
    existing_df = doc_table.select(
        doc_table.doc_id, doc_table.document, doc_table.keyword, doc_table.examples_raw
    ).collect().to_pandas()
    new_doc_data = doc.model_dump()
    max_similarity = 0.0
    duplicate_with_id = None
    duplicate_with_name = ""

    if len(existing_df) > 0:
        for _, row in existing_df.iterrows():
            existing_doc = row.to_dict()
            sim = calculate_document_similarity(new_doc_data, existing_doc)
            if sim > max_similarity:
                max_similarity = sim
                duplicate_with_id = int(row['doc_id'])
                duplicate_with_name = str(row['document'])

    data = doc.model_dump()
    data['similarity_score'] = round(max_similarity, 1)
    data['duplicate_with_id'] = duplicate_with_id
    data['duplicate_with_name'] = duplicate_with_name[:100] if duplicate_with_name else ""

    num_examples = insert_document_with_examples(doc_table, examples_table, data, doc_id)
    log_func("add_document", f"Document added with {num_examples} examples", debug_level=1)

    # Reset corpus stats cache since documents changed
    reset_all_caches()

    return {"status": "success", "message": f"Document added with {num_examples} examples", "doc_id": doc_id}


@app.get("/documents/{idx}")
def get_document(idx: int):
    """Lấy document theo doc_id"""
    log_func("get_document", f"Getting document doc_id={idx}", debug_level=2)
    doc_table, _ = get_tables()
    df = doc_table.select().collect().to_pandas()
    doc_row = df[df['doc_id'] == idx]

    if len(doc_row) == 0:
        raise HTTPException(404, f"Document with doc_id={idx} not found")

    result = doc_row.iloc[0].to_dict()
    if 'examples_raw' in result:
        result['examples'] = result.pop('examples_raw')

    return result


@app.put("/documents/{idx}")
def update_document(idx: int, doc: Document):
    """
    Cập nhật document theo doc_id.
    Sử dụng phương pháp delete + re-insert vì Pixeltable không hỗ trợ UPDATE trực tiếp.
    """
    log_func("update_document", f"Updating document doc_id={idx}", debug_level=1)

    doc_table, examples_table = get_tables()

    # Check if document exists
    existing_df = doc_table.select().collect().to_pandas()
    doc_row = existing_df[existing_df['doc_id'] == idx]

    if len(doc_row) == 0:
        raise HTTPException(404, f"Document with doc_id={idx} not found")

    # Delete old examples
    old_examples_count = examples_table.where(examples_table.doc_id == idx).count()
    examples_table.where(examples_table.doc_id == idx).delete()
    log_func("update_document", f"Deleted {old_examples_count} old examples", debug_level=2)

    # Delete old document
    doc_table.where(doc_table.doc_id == idx).delete()
    log_func("update_document", f"Deleted old document", debug_level=2)

    # Re-insert with same doc_id
    data = doc.model_dump()

    # Keep similarity info from old record if not provided
    old_record = doc_row.iloc[0]
    data['similarity_score'] = float(old_record.get('similarity_score', 0.0) or 0.0)

    # Handle duplicate_with_id - convert from float64/NaN to int/None
    dup_id = old_record.get('duplicate_with_id')
    if pd.isna(dup_id):
        data['duplicate_with_id'] = None
    else:
        data['duplicate_with_id'] = int(dup_id)

    data['duplicate_with_name'] = str(old_record.get('duplicate_with_name', '') or '')

    num_examples = insert_document_with_examples(doc_table, examples_table, data, idx)
    log_func("update_document", f"Document updated with {num_examples} examples", debug_level=1)

    # Reset all caches since data changed
    reset_all_caches()

    # Force rebuild embeddings cache
    build_embeddings_cache(doc_table, examples_table, force_rebuild=True)

    return {
        "status": "success",
        "message": f"Document doc_id={idx} updated with {num_examples} examples",
        "doc_id": idx,
        "num_examples": num_examples
    }


@app.delete("/documents/{idx}")
def delete_document(idx: int):
    """Xoá document và examples của nó - sử dụng Pixeltable native delete"""
    log_func("delete_document", f"Deleting document doc_id={idx}", debug_level=1)

    doc_table, examples_table = get_tables()

    # Check if document exists
    doc_count = doc_table.where(doc_table.doc_id == idx).count()
    if doc_count == 0:
        raise HTTPException(404, f"Document with doc_id={idx} not found")

    # Count examples to delete
    examples_count = examples_table.where(examples_table.doc_id == idx).count()

    # Delete examples first (child records)
    examples_table.where(examples_table.doc_id == idx).delete()
    log_func("delete_document", f"Deleted {examples_count} examples", debug_level=1)

    # Delete document
    doc_table.where(doc_table.doc_id == idx).delete()
    log_func("delete_document", f"Document doc_id={idx} deleted", debug_level=1)

    # Reset caches since documents changed
    reset_all_caches()

    return {"status": "success", "message": f"Document doc_id={idx} and {examples_count} examples deleted"}


@app.delete("/documents")
def delete_all_documents():
    """Xoá tất cả documents"""
    log_func("delete_all_documents", "⚠️ User requested DELETE ALL...", debug_level=0)
    drop_and_create_tables()  # Chỉ function này mới xóa dữ liệu

    # Reset corpus stats cache since documents changed
    reset_all_caches()

    return {"status": "success", "message": "All documents deleted"}


@app.post("/documents/upload")
async def upload_documents(files: List[UploadFile] = File(...)):
    """Upload nhiều file Excel"""
    log_func("upload_documents", f"Uploading {len(files)} files", debug_level=1)

    doc_table, examples_table = get_tables()
    existing_df = doc_table.select(
        doc_table.doc_id, doc_table.document, doc_table.keyword, doc_table.examples_raw
    ).collect().to_pandas()

    all_records = []
    file_stats = []
    next_doc_id = get_next_doc_id(doc_table)

    for file in files:
        if not file.filename.endswith(('.xlsx', '.xls')):
            file_stats.append({"filename": file.filename, "status": "error", "message": "Invalid file type"})
            continue

        try:
            df = pd.read_excel(file.file)
            if 'document' not in df.columns:
                file_stats.append({"filename": file.filename, "status": "error", "message": "Missing 'document' column"})
                continue

            records = df.fillna('').to_dict(orient='records')
            for r in records:
                r['_source_file'] = file.filename
                # Parse metadata
                if 'metadata' in r and isinstance(r['metadata'], str) and r['metadata'].strip():
                    try:
                        r['metadata'] = json.loads(r['metadata'])
                    except:
                        r['metadata'] = {"raw_text": r['metadata']}
                elif 'metadata' not in r or not r['metadata']:
                    r['metadata'] = {}

                all_records.append(r)

            file_stats.append({"filename": file.filename, "status": "success", "count": len(records)})
        except Exception as e:
            file_stats.append({"filename": file.filename, "status": "error", "message": str(e)})

    if not all_records:
        return {"status": "error", "message": "No valid records", "files": file_stats}

    # Check duplicates và insert
    results = []
    total_examples = 0

    for r in all_records:
        max_sim = 0.0
        dup_id = None
        dup_name = ""

        # Check với existing (dùng nhiều trường để tính similarity)
        if len(existing_df) > 0:
            for _, row in existing_df.iterrows():
                existing_doc = row.to_dict()
                sim = calculate_document_similarity(r, existing_doc)
                if sim > max_sim:
                    max_sim = sim
                    dup_id = int(row['doc_id'])
                    dup_name = str(row['document'])

        r['similarity_score'] = round(max_sim, 1)
        r['duplicate_with_id'] = dup_id
        r['duplicate_with_name'] = dup_name[:100]

        source_file = r.pop('_source_file', '')
        num_ex = insert_document_with_examples(doc_table, examples_table, r, next_doc_id)
        total_examples += num_ex

        doc_name = str(r.get('document', ''))
        warning = "⛔ Trùng lặp" if max_sim >= 95 else ("⚠️ Có thể trùng" if max_sim >= 80 else "✅ OK")
        results.append({
            "document": doc_name[:80],
            "source_file": source_file,
            "similarity": round(max_sim, 1),
            "warning": warning,
            "num_examples": num_ex
        })

        next_doc_id += 1

    log_func("upload_documents", f"Inserted {len(all_records)} docs with {total_examples} examples", debug_level=1)

    # Reset corpus stats cache since documents changed
    reset_all_caches()

    return {
        "status": "success",
        "message": f"{len(all_records)} documents added with {total_examples} examples",
        "total_records": len(all_records),
        "total_examples": total_examples,
        "files": file_stats,
        "results": results
    }


# ============================================================================
# SEARCH ENDPOINTS - MAX SIMILARITY ARCHITECTURE
# ============================================================================

@app.post("/search")
def search_single(query: SearchQuery):
    """Tra cứu với HYBRID SEARCH: Semantic + BM25 + Keyword Boosting

    Algorithm (Expert-level):
    1. Query Normalization: Chuẩn hóa query (expand abbr, remove fillers)
    2. Semantic Search: Embedding similarity với examples (MAX) và search_text
    3. BM25 Search: Keyword matching với documents và examples
    4. Keyword Boosting: Boost score nếu query chứa keywords từ document
    5. Final score = SEMANTIC * 0.6 + BM25 * 0.25 + KEYWORD_BOOST * 0.15
    """
    t={}
    t[1]=time.perf_counter()
    log_func("search_single", f"Searching: '{query.query[:50]}...' (top_k={query.top_k})", debug_level=1)
    t[2]=time.perf_counter()
    doc_table, examples_table = get_tables()
    t[3]=time.perf_counter()
    # Use the centralized hybrid search function
    results = perform_hybrid_search(query.query, doc_table, examples_table, query.top_k)
    t[4]=time.perf_counter()
    log_func("search_single", f"Found {len(results)} results", debug_level=1)
    if results:
        top = results[0]
        log_func("search_single",
                f"Top: {top['document']}... (score={top['score']:.4f}, sem={top['score_semantic']:.4f}, bm25={top['score_bm25']:.4f}, boost={top['score_keyword_boost']:.4f})",
                debug_level=2)
    # t[5]=time.perf_counter()
    # keys = sorted(t.keys())
    # for k1, k2 in zip(keys, keys[1:]):
    #     dt = t[k2] - t[k1]
    #     print(f"search: {k1} → {k2}: {dt*1000:>12.3f} miliseconds")
    # print(f'search: total: {(t[5]-t[1])*1000:>12.3f} miliseconds')
    return results

@app.post("/chatbot/intent_recognition", tags=["Chatbot"])
async def intent_recognition(item: inputIntentRecognition):
    """API nhận diện intent theo format của hệ thống.

    ví dụ:
    ```
       {
        "question": "Xem chi tiết tk của tôi."
        }
    ```
    Returns:
     ```
     {
        "status": 1,
        "groupIntent": "",
        "intent": "API getAccountDetail",
        "options": [],
        "score": 0.8685,
        "question": "xem chi tiết tài khoản của tôi."
        }
     ```   
    """
    question = normalize_text(item.question) or ""
    question_normalized = vietnamese_normalizer.normalize_for_intent(question)
    itemSearchQuery=SearchQuery(query=question_normalized, top_k=config.DEFAULT_TOP_K)     
    
    KQ=search_single(query=itemSearchQuery)
    
    # results.append({
    #         'document': row['document'],
    #         'metadata': row['metadata'],
    #         'description': row['description'],
    #         'examples': row['examples_raw'],
    #         'keyword': row['keyword'],
    #         'score': round(float(row['score']), 4),
    #         'score_semantic': round(float(row['semantic_score']), 4),
    #         'score_max_example': round(float(row['max_example_score']), 4),
    #         'score_search_text': round(float(row['search_score']), 4),
    #         'score_bm25': round(float(row['bm25_normalized']), 4),
    #         'score_keyword_boost': round(float(row['keyword_boost']), 4),
    #         'best_matching_example': row.get('best_example', ''),
    #         'classified_intent': classified_intent
    #     })
    # print(KQ)
    
    return outputIntentRecognition(status=1, 
                                   groupIntent="", 
                                   intent=KQ[0]['document'], 
                                   options=[], 
                                   score=float(KQ[0]['score']), 
                                   question=question_normalized)

def _get_client_ip(request: Request) -> str:
    """Lấy IP của client từ request headers hoặc client host"""
    # Thử lấy từ X-Forwarded-For (nếu qua proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # X-Forwarded-For có thể chứa nhiều IP, lấy IP đầu tiên
        return forwarded.split(",")[0].strip()

    # Thử lấy từ X-Real-IP
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fallback: lấy từ client host
    if request.client:
        return request.client.host

    return "unknown"


def _sanitize_filename(filename: str) -> str:
    """Loại bỏ các ký tự không hợp lệ trong tên file"""
    # Loại bỏ extension
    name = filename.rsplit('.', 1)[0] if '.' in filename else filename
    # Thay thế các ký tự không hợp lệ
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '_')
    # Giới hạn độ dài
    return name[:50]


def _process_batch_search(file_content: bytes, top_k: int, original_filename: str, client_ip: str) -> tuple:
    """
    Synchronous batch search processing - runs in thread pool.
    Returns: (output_path, error_message)
    """
    import io

    df = pd.read_excel(io.BytesIO(file_content))
    if 'query' not in df.columns and 'question' not in df.columns:
        return None, "Excel must have 'query' or 'question' column"

    colQuery = 'query' if 'query' in df.columns else 'question'
    api_col = next((c for c in df.columns if c.lower().strip() == 'api'), None)
    df = df.dropna(subset=[colQuery])
    df = df[df[colQuery].astype(str).str.strip() != '']

    doc_table, examples_table = get_tables()
    all_results = []

    for i, row in df.iterrows():
        query_text = str(row[colQuery]).strip()
        if not query_text:
            continue
        log_func("search_batch","==========================================", debug_level=3)
        # Use hybrid search
        search_results = perform_hybrid_search(query_text, doc_table, examples_table, top_k)

        if not search_results:
            continue

        # Add to results
        for result in search_results:
            result_row = {
                'input_query': query_text,
                'score': result['score'],
                'score_semantic': result['score_semantic'],
                'score_bm25': result['score_bm25'],
                'score_keyword_boost': result['score_keyword_boost'],
                'document': result['document'],
                'best_matching_example': result.get('best_matching_example', ''),
                'classified_intent': result.get('classified_intent', ''),
            }

            if api_col:
                expected_api = str(row[api_col]).strip() if pd.notna(row[api_col]) else ''
                result_row['expected_API'] = expected_api

                if expected_api:
                    doc_lower = str(result['document']).lower()
                    api_lower = expected_api.lower()
                    result_row['is_match'] = 'Yes' if api_lower in doc_lower or doc_lower in api_lower else ''

            all_results.append(result_row)

    if not all_results:
        return None, "No valid queries found"

    output_df = pd.DataFrame(all_results)

    # Reorder columns
    cols_order = ['input_query']
    if api_col:
        cols_order.extend(['expected_API', 'is_match'])
    cols_order.extend(['score', 'score_semantic', 'score_bm25', 'score_keyword_boost',
                       'document', 'best_matching_example', 'classified_intent'])
    cols_order = [c for c in cols_order if c in output_df.columns]
    output_df = output_df[cols_order]

    # Build filename: tên_gốc_IP_thời_gian.xlsx
    safe_filename = _sanitize_filename(original_filename)
    safe_ip = client_ip.replace(":", "-").replace(".", "-")  # IPv6 dùng ":", IPv4 dùng "."
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = config.OUTPUT_DIR / f"{safe_filename}_{safe_ip}_{timestamp}.xlsx"
    output_df.to_excel(output_path, index=False)

    log_func("search_batch", f"Results saved to: {output_path}", debug_level=1)
    return output_path, None


@app.post("/search/batch")
async def search_batch(request: Request, file: UploadFile = File(...), top_k: int = config.DEFAULT_TOP_K):
    """Tra cứu batch với HYBRID SEARCH: Semantic + BM25 + Keyword Boosting.
    Non-blocking: runs in thread pool to avoid blocking event loop.
    """
    import asyncio

    log_func("search_batch", f"Batch search from: {file.filename}", debug_level=1)

    if not str(file.filename).endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "File must be Excel")

    # Get client IP and original filename
    client_ip = _get_client_ip(request)
    original_filename = file.filename or "batch"

    # Read file content first (async)
    file_content = await file.read()

    # Run blocking operations in thread pool
    loop = asyncio.get_event_loop()
    output_path, error = await loop.run_in_executor(
        _executor,
        _process_batch_search,
        file_content,
        top_k,
        original_filename,
        client_ip
    )

    if error:
        raise HTTPException(400, error)

    return FileResponse(output_path, filename=output_path.name,
                       media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.post("/search/batch/stream")
async def search_batch_stream(request: Request, file: UploadFile = File(...), top_k: int = config.DEFAULT_TOP_K):
    """Tra cứu batch với SSE streaming + HYBRID SEARCH"""
    log_func("search_batch_stream", f"Batch stream search from: {file.filename}", debug_level=1)

    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(400, "File must be Excel")

    # Get client IP and original filename BEFORE entering async generator
    client_ip = _get_client_ip(request)
    original_filename = file.filename or "batch"

    # Read file content into memory for processing
    file_content = await file.read()

    async def generate_events():
        """Generator cho SSE events"""
        import io
        import asyncio
        start_time = time.time()

        # Build filename prefix: tên_gốc_IP_thời_gian
        safe_filename = _sanitize_filename(original_filename)
        safe_ip = client_ip.replace(":", "-").replace(".", "-")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename_prefix = f"{safe_filename}_{safe_ip}_{timestamp}"

        try:
            df = pd.read_excel(io.BytesIO(file_content))
            if 'query' not in df.columns:
                yield f"data: {json.dumps({'error': 'Excel must have query column'})}\n\n"
                return

            has_api_column = 'API' in df.columns
            df = df.dropna(subset=['query'])
            df = df[df['query'].astype(str).str.strip() != '']

            total_rows = len(df)
            if total_rows == 0:
                yield f"data: {json.dumps({'error': 'No valid queries found'})}\n\n"
                return
            print("total_rows:", total_rows)
            # Send initial info
            yield f"data: {json.dumps({'type': 'init', 'total': total_rows})}\n\n"

            # Send "loading" status before potentially slow operations
            yield f"data: {json.dumps({'type': 'status', 'message': 'Đang tải model embedding...'})}\n\n"
            await asyncio.sleep(0)  # Force flush to client

            # Run blocking operation in thread pool to not block event loop
            # NOTE: Use run_in_executor instead of asyncio.to_thread for nest_asyncio compatibility
            loop = asyncio.get_event_loop()
            doc_table, examples_table = await loop.run_in_executor(_executor, get_tables)

            # Send "ready" status after tables loaded
            yield f"data: {json.dumps({'type': 'status', 'message': 'Đang xây dựng index BM25...'})}\n\n"
            await asyncio.sleep(0)  # Force flush to client

            # Pre-build corpus stats (can take time on first run)
            _ = await loop.run_in_executor(_executor, get_corpus_stats, doc_table, examples_table)

            yield f"data: {json.dumps({'type': 'status', 'message': 'Sẵn sàng! Đang tra cứu...'})}\n\n"
            await asyncio.sleep(0)  # Force flush to client

            all_results = []
            processed = 0

            # Initialize output path for incremental save
            output_path = config.OUTPUT_DIR / f"{filename_prefix}.xlsx"
            save_counter = 0  # Track save attempts for fallback filename

            def save_checkpoint(results_list, path, counter):
                """Save results with fallback filename if file is locked"""
                if not results_list:
                    return path, counter

                checkpoint_df = pd.DataFrame(results_list)

                # Reorder columns
                cols_order = ['input_query']
                if has_api_column:
                    cols_order.extend(['expected_API', 'is_match'])
                cols_order.extend(['score', 'score_semantic', 'score_bm25', 'score_keyword_boost',
                                   'document', 'best_matching_example', 'classified_intent',
                                   'description', 'examples', 'keyword', 'metadata'])
                cols_order = [c for c in cols_order if c in checkpoint_df.columns]
                checkpoint_df = checkpoint_df[cols_order]

                try:
                    checkpoint_df.to_excel(path, index=False)
                    return path, counter
                except PermissionError:
                    # File is locked (Excel open), create new filename
                    counter += 1
                    new_path = config.OUTPUT_DIR / f"{filename_prefix}_v{counter}.xlsx"
                    log_func("save_checkpoint", f"File locked, saving to: {new_path}", debug_level=1)
                    checkpoint_df.to_excel(new_path, index=False)
                    return new_path, counter

            for i, row in df.iterrows():
                row_start = time.time()
                query_text = str(row['query']).strip()
                if not query_text:
                    continue

                # Run tokenization and search in thread pool to avoid blocking
                # NOTE: Use run_in_executor instead of asyncio.to_thread for nest_asyncio compatibility
                def process_single_query(q_text: str):
                    tokens = q_text.split()
                    tokens = tafix_tokens(tokens)
                    fixed_query = ' '.join(tokens)
                    return fixed_query, perform_hybrid_search(fixed_query, doc_table, examples_table, top_k)

                query_text, search_results = await loop.run_in_executor(_executor, process_single_query, query_text)

                if not search_results:
                    processed += 1
                    continue

                # Add to results
                for result in search_results:
                    result_row = {
                        'input_query': query_text,
                        'score': result['score'],
                        'score_semantic': result['score_semantic'],
                        'score_bm25': result['score_bm25'],
                        'score_keyword_boost': result['score_keyword_boost'],
                        'document': result['document'],
                        'best_matching_example': result.get('best_matching_example', ''),
                        'classified_intent': result.get('classified_intent', ''),
                        # 'description': result['description'],
                        # 'examples': result['examples'],
                        # 'keyword': result['keyword'],
                        # 'metadata': result['metadata']
                    }

                    if has_api_column:
                        expected_api = str(row.get('API', '')).strip() if pd.notna(row.get('API')) else ''
                        result_row['expected_API'] = expected_api
                        if expected_api:
                            doc_lower = str(result['document']).lower()
                            api_lower = expected_api.lower()
                            result_row['is_match'] = 1 if (api_lower in doc_lower or doc_lower in api_lower) else 0

                    all_results.append(result_row)

                processed += 1
                row_time = time.time() - row_start
                elapsed = time.time() - start_time

                # Send progress update
                progress_data = {
                    'type': 'progress',
                    'processed': processed,
                    'total': total_rows,
                    'percent': round((processed / total_rows) * 100, 1),
                    'elapsed': round(elapsed, 1),
                    'row_time': round(row_time, 3),
                    'query_preview': query_text[:50] + ('...' if len(query_text) > 50 else '')
                }

                # Estimate remaining time based on average
                if processed > 0:
                    avg_per_row = elapsed / processed
                    remaining = (total_rows - processed) * avg_per_row
                    progress_data['remaining'] = round(remaining, 1)
                    progress_data['avg_per_row'] = round(avg_per_row, 3)

                yield f"data: {json.dumps(progress_data)}\n\n"
                await asyncio.sleep(0)  # Force flush progress to client

                # Incremental save every 100 rows (avoid data loss on crash)
                if processed % 100 == 0 and processed > 0:
                    output_path, save_counter = save_checkpoint(all_results, output_path, save_counter)
                    yield f"data: {json.dumps({'type': 'status', 'message': f'💾 Checkpoint saved ({processed}/{total_rows}) → {output_path.name}'})}\n\n"
                    await asyncio.sleep(0)

            # Final save (all results)
            if not all_results:
                yield f"data: {json.dumps({'error': 'No results generated'})}\n\n"
                return

            # Final save using checkpoint function (handles locked files)
            output_path, save_counter = save_checkpoint(all_results, output_path, save_counter)

            total_time = time.time() - start_time
            avg_time = total_time / total_rows if total_rows > 0 else 0

            # Send completion event
            complete_data = {
                'type': 'complete',
                'filename': output_path.name,
                'total_rows': total_rows,
                'total_time': round(total_time, 2),
                'avg_per_row': round(avg_time, 3)
            }
            yield f"data: {json.dumps(complete_data)}\n\n"

            log_func("search_batch_stream", f"Completed in {total_time:.2f}s, avg {avg_time:.3f}s/row, saved to {output_path.name}", debug_level=1)

        except Exception as e:
            log_func("search_batch_stream", f"Error: {str(e)}", debug_level=0)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================================
# UTILITY ENDPOINTS
# ============================================================================

@app.get("/outputs")
def list_outputs():
    """List output files"""
    files = list(config.OUTPUT_DIR.glob("*.xlsx"))
    result = []
    for f in files:
        stat = f.stat()
        result.append({
            "filename": f.name,
            "created": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "size": stat.st_size
        })
    return result


@app.get("/outputs/{filename}")
def download_output(filename: str):
    """Download output file"""
    path = config.OUTPUT_DIR / filename
    if not path.exists():
        raise HTTPException(404, "File not found")
    return FileResponse(path, filename=filename)


@app.get("/template/query")
def download_query_template():
    """Download query template"""
    path = config.TEMPLATE_DIR / "query_template.xlsx"
    if not path.exists():
        pd.DataFrame({"query": ["Câu hỏi mẫu 1", "Câu hỏi mẫu 2"]}).to_excel(path, index=False)
    return FileResponse(path, filename="query_template.xlsx")


@app.get("/template/document")
def download_document_template():
    """Download document template"""
    path = config.TEMPLATE_DIR / "document_template.xlsx"
    if not path.exists():
        raise HTTPException(404, "Template not found")
    return FileResponse(path, filename="document_template.xlsx")


def _sanitize_text_for_export(text):
    """
    Chuẩn hóa text trước khi export ra Excel.
    - Thay dấu nháy đơn cong thành dấu nháy đơn thẳng
    - Thay dấu nháy kép cong thành dấu nháy kép thẳng
    """
    if not isinstance(text, str):
        return text

    # Thay các dấu nháy đơn cong/đặc biệt thành dấu nháy thẳng
    # text = text.replace("'", "'").replace("'", "'").replace("`", "'")
    # Thay các dấu nháy kép cong thành dấu nháy kép thẳng
    text = text.replace("'", '"').replace("„", '"')
    return text


def _convert_metadata_to_json(value):
    """
    Convert metadata sang JSON format chuẩn (dùng dấu nháy kép).
    - Dict/List -> json.dumps()
    - String dạng Python dict -> parse rồi json.dumps()
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""

    # Nếu đã là dict/list -> convert sang JSON string
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)

    # Nếu là string, thử parse như Python dict rồi convert sang JSON
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return ""
        # Nếu đã là JSON format (bắt đầu bằng { hoặc [) -> giữ nguyên
        if text.startswith('{') or text.startswith('['):
            try:
                # Thử parse như JSON trước
                parsed = json.loads(text)
                return json.dumps(parsed, ensure_ascii=False)
            except json.JSONDecodeError:
                # Không phải JSON, có thể là Python dict format
                try:
                    import ast
                    parsed = ast.literal_eval(text)
                    return json.dumps(parsed, ensure_ascii=False)
                except (ValueError, SyntaxError):
                    return text
        return text

    return str(value)


def _sanitize_df_for_export(df):
    """Chuẩn hóa toàn bộ DataFrame trước khi export."""
    df = df.copy()

    # Sanitize text columns
    text_cols = ['document', 'description', 'examples', 'keyword']
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].apply(_sanitize_text_for_export)

    # Convert metadata sang JSON format chuẩn (dùng dấu nháy kép)
    if 'metadata' in df.columns:
        df['metadata'] = df['metadata'].apply(_convert_metadata_to_json)

    return df


@app.get("/api/export/documents")
def export_all_documents():
    """
    Export tất cả documents ra file Excel để backup.
    Mỗi lần export tạo file mới với timestamp.
    """
    import io

    log_func("export_all_documents", "Exporting all documents...", debug_level=1)

    doc_table, _ = get_tables()
    docs_df = doc_table.select().collect().to_pandas()

    if len(docs_df) == 0:
        raise HTTPException(404, "No documents to export")

    # Rename examples_raw to examples for export
    if 'examples_raw' in docs_df.columns:
        docs_df = docs_df.rename(columns={'examples_raw': 'examples'})

    # Select and reorder columns for export
    export_cols = ['doc_id', 'document', 'description', 'examples', 'keyword', 'metadata']
    export_cols = [c for c in export_cols if c in docs_df.columns]
    export_df = docs_df[export_cols]

    # Sanitize text columns
    export_df = _sanitize_df_for_export(export_df)

    # Create Excel file in memory
    output = io.BytesIO()
    export_df.to_excel(output, index=False, sheet_name='Documents')
    output.seek(0)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"kb_backup_all_{timestamp}.xlsx"

    log_func("export_all_documents", f"Exported {len(docs_df)} documents to {filename}", debug_level=1)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/api/export/document/{doc_id}")
def export_single_document(doc_id: int):
    """
    Export một document ra file Excel để backup.
    """
    import io

    log_func("export_single_document", f"Exporting document doc_id={doc_id}...", debug_level=1)

    doc_table, examples_table = get_tables()
    docs_df = doc_table.select().collect().to_pandas()

    # Filter for specific document
    doc_row = docs_df[docs_df['doc_id'] == doc_id]

    if len(doc_row) == 0:
        raise HTTPException(404, f"Document with doc_id={doc_id} not found")

    # Rename examples_raw to examples for export
    if 'examples_raw' in doc_row.columns:
        doc_row = doc_row.rename(columns={'examples_raw': 'examples'})

    # Select and reorder columns for export
    export_cols = ['doc_id', 'document', 'description', 'examples', 'keyword', 'metadata']
    export_cols = [c for c in export_cols if c in doc_row.columns]
    export_df = doc_row[export_cols]

    # Sanitize text columns (same as export_all_documents)
    export_df = _sanitize_df_for_export(export_df)

    # Create Excel file in memory
    output = io.BytesIO()
    export_df.to_excel(output, index=False, sheet_name='Document')
    output.seek(0)

    # Generate filename with document name and timestamp
    doc_name = str(doc_row.iloc[0]['document']).replace(' ', '_').replace('/', '_')[:30]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"kb_backup_{doc_name}_{timestamp}.xlsx"

    log_func("export_single_document", f"Exported document '{doc_name}' to {filename}", debug_level=1)

    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.get("/stats")
def get_stats():
    """Thống kê database"""
    doc_table, examples_table = get_tables()
    doc_count = len(doc_table.select().collect().to_pandas())
    example_count = len(examples_table.select().collect().to_pandas())

    return {
        "total_documents": doc_count,
        "total_examples": example_count,
        "avg_examples_per_doc": round(example_count / doc_count, 1) if doc_count > 0 else 0,
        "embedding_model": config.EMBEDDING_MODEL,
        "weights": {
            "examples": config.EXAMPLES_WEIGHT,
            "search_text": config.SEARCH_TEXT_WEIGHT
        }
    }


if __name__ == "__main__":
    import uvicorn
    log_func("main", "Starting server...", debug_level=1)
    uvicorn.run(app, host="0.0.0.0", port=8000)
