import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
TEMPLATE_STORE_DIR = os.path.join(BASE_DIR, "template_store")

# ─── Database ───────────────────────────────────────────────
DB_HOST = "192.168.3.7"
DB_PORT = 3306
DB_USER = "bank-gateway"
DB_PASSWORD = "bankgateway@123"
DB_NAME = "ai_bank_gateway"

# ─── Domain Routing ─────────────────────────────────────────
DEFAULT_DOMAIN_ID = "banking"
DOMAINS_BASE_DIR = os.path.join(DATA_DIR, "domains")
DOMAIN_REGISTRY_PATH = os.path.join(DOMAINS_BASE_DIR, "registry.json")
DOMAIN_SHORTLIST_SCORE_GAP = 0.15
DOMAIN_SHORTLIST_RELATIVE_THRESHOLD = 0.7
DOMAIN_AMBIGUITY_TOLERANCE = 0.05

# ─── Paths ──────────────────────────────────────────────────
SEMANTIC_PROFILES_DIR = os.path.join(BASE_DIR, "data", "semantic_profiles")
INTENT_DATASET_PATH = os.path.join(BASE_DIR, "data", "user_intent", "ddq_document_v2.json")
APPROVED_TEMPLATES_DIR = os.path.join(BASE_DIR, "template_store", "approved_templates")
USER_QUESTIONS_DIR = os.path.join(BASE_DIR, "data", "user_questions")
LOGS_DIR = os.path.join(BASE_DIR, "logs")
LEGACY_SEMANTIC_PROFILES_DIR = SEMANTIC_PROFILES_DIR
LEGACY_INTENT_DATASET_PATH = INTENT_DATASET_PATH
LEGACY_APPROVED_TEMPLATES_DIR = APPROVED_TEMPLATES_DIR

# ─── LLM ────────────────────────────────────────────────────
# Supported backends: "openai_compatible" | "ollama" | "transformers"
LLM_BACKEND = "openai_compatible"

# OpenAI-compatible API (current serving endpoint)
LLM_API_BASE_URL = "http://192.168.3.7:6805/v1"
LLM_API_KEY = "EMPTY"
LLM_API_MODEL = "qwen3.5-9b"

# Ollama fallback
LLM_OLLAMA_BASE_URL = "http://localhost:11434"
LLM_OLLAMA_MODEL = "llama3:8b"

# Transformers fallback
LLM_MODEL_PATH = ""             # HF path (only for transformers backend)
LLM_MAX_NEW_TOKENS = 2048        # Increased to handle extended thinking + SQL generation
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
