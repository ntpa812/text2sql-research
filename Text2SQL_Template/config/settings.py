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
LOGS_DIR = os.path.join(BASE_DIR, "logs")

# ─── LLM ────────────────────────────────────────────────────
LLM_MODEL_PATH = os.path.join(BASE_DIR, "models", "mars-sql", "mars-sql_qwen_sql_7b")
LLM_MAX_NEW_TOKENS = 256
LLM_TEMPERATURE = 0.1

# ─── NER (in 6804_DDQ) ─────────────────────────────────────
NER_MODEL_PATH = os.path.join(
    BASE_DIR, os.pardir, "6804_DDQ", "data_models", "ner_model"
)

# ─── Pipeline ───────────────────────────────────────────────
MAX_RETRY_ATTEMPTS = 3
QUERY_ROW_LIMIT = 100
QUERY_TIMEOUT_SECONDS = 30

# ─── Embedding (for intent ranking / schema routing) ───────
EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-base"

# ─── Blocked SQL keywords ──────────────────────────────────
BLOCKED_SQL_KEYWORDS = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE"]
