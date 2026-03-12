import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ─── Database ───────────────────────────────────────────────
DB_HOST = "192.168.3.7"
DB_PORT = 3306
DB_USER = "bank-gateway"
DB_PASSWORD = "bankgateway@123"
DB_NAME = "ai_bank_gateway"

# ─── Paths ──────────────────────────────────────────────────
SEMANTIC_PROFILES_DIR = os.path.join(BASE_DIR, "data", "semantic_profiles")
INTENT_DATASET_PATH = os.path.join(BASE_DIR, "data", "user_intent", "ddq_document_v2.json")
APPROVED_TEMPLATES_DIR = os.path.join(BASE_DIR, "template_store", "approved_templates")
USER_QUESTIONS_DIR = os.path.join(BASE_DIR, "data", "user_questions")
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# ─── LLM (Llama 3 via Ollama) ───────────────────────────────
LLM_BACKEND = "ollama"          # "ollama" | "transformers"
LLM_OLLAMA_BASE_URL = "http://localhost:11434"
LLM_OLLAMA_MODEL = "llama3:8b"  # ollama model name
# LLM_OLLAMA_MODEL = "kwangsuklee/Qwen3.5-4B-Claude-4.6-Opus-Reasoning-Distilled-GGUF:latest"
# LLM_OLLAMA_MODEL = "hf.co/defog/sqlcoder-7b-2:Q5_K_M"
LLM_MODEL_PATH = ""             # HF path (only for transformers backend)
LLM_MAX_NEW_TOKENS = 256
LLM_TEMPERATURE = 0.0

# ─── NER (in 6804_DDQ) ─────────────────────────────────────
NER_MODEL_PATH = os.path.join(
    BASE_DIR, os.pardir, "6804_DDQ", "data_models", "ner_model"
)

# ─── Pipeline ───────────────────────────────────────────────
MAX_RETRY_ATTEMPTS = 2
QUERY_ROW_LIMIT = 100
QUERY_TIMEOUT_SECONDS = 30

# ─── Testing ────────────────────────────────────────────────
# Mock account for offline testing (inject vào SQL khi test)
TEST_MODE = False
TEST_ACCOUNT = "1234567890"
TEST_CUSTOMER_ID = "CUS001"

# ─── Embedding (for intent ranking / schema routing) ───────
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-base"
EMBEDDING_CACHE_DIR = os.path.join(BASE_DIR, "cache")

# ─── Blocked SQL keywords ──────────────────────────────────
BLOCKED_SQL_KEYWORDS = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE"]
