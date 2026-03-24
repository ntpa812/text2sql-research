# Multi-domain Text2SQL Pipeline

Hệ thống chuyển đổi câu hỏi tiếng Việt thành SQL cho nhiều domain/database khác nhau như `banking`, `hrm`. Hệ thống dùng một `domain router` không dùng LLM để chọn domain/database trước khi chọn table và sinh SQL.

## Luồng xử lý (9 bước)

```
User Question (Vietnamese)
        │
   ┌────┴────┐
   │  Step 0  │  Domain Router        ← chọn domain/database (non-LLM)
   └────┬────┘
        │
   ┌────┴────┐
   │  Step 1  │  Schema Router        ← chọn bảng liên quan trong domain đã chọn
   └────┬────┘
        │
   ┌────┴────┐
   │  Step 2  │  Intent Detection     ← nhận diện intent từ dataset theo domain
   └────┬────┘
        │
   ┌────┴────┐
   │  Step 3  │  Entity Extraction    ← NER local (6804_DDQ) + regex fallback
   └────┬────┘
        │
   ┌────┴────┐
   │  Step 4  │  Template Retrieval   ← lấy approved SQL template + slot filling
   └────┬────┘
        │
   ┌────┴────┐
   │  Step 5  │  SQL Generation       ← Template-first (skip LLM nếu fill đủ) hoặc LLM
   └────┬────┘                          (retry max 3: syntax → schema → logic)
        │
   ┌────┴────┐
   │  Step 6  │  Validator            ← security → syntax → schema check
   └────┬────┘
        │
   ┌────┴────┐
   │  Step 7  │  Execute on DB        ← execute trên DB config của domain đã chọn
   └────┬────┘
        │
   ┌────┴────┐
   │  Step 8  │  Explain Engine       ← giải thích kết quả bằng tiếng Việt
   └─────────┘
```

## Cấu trúc thư mục

```
Text2SQL_Template/
│
├── app.py                          # Entry point (interactive + batch mode)
├── test_domain_routing.py          # Regression tests cho domain routing
│
├── config/
│   ├── settings.py                 # Settings chung + domain registry path
│   └── db_connector.py             # MySQL schema loader theo db_config
│
├── domain_router/
│   ├── registry_loader.py          # Load domain registry
│   └── selector.py                 # Chọn/shortlist domain bằng keyword + embedding
│
├── pipeline/
│   ├── pipeline_runner.py          # Orchestrator chính (domain-aware)
│   └── retry_handler.py            # Retry strategy (3 levels)
│
├── schema_router/
│   ├── schema_loader.py            # Load semantic profiles
│   └── table_selector.py           # Rank bảng theo domain
│
├── intent_detection/
│   ├── intent_loader.py            # Load intent dataset JSON
│   └── intent_ranker.py            # Ranking intent (keyword + cached embedding)
│
├── entity_extraction/
│   ├── ner_local.py                # NER local (wrapper 6804_DDQ) + regex fallback
│   └── ner_fallback_llm.py         # Fallback: LLM entity extraction
│
├── dataset_loader/
│   └── question_loader.py          # Load questions từ json/csv/xlsx/md
│
├── template_store/
│   ├── template_loader.py          # Load/save approved templates
│   └── approved_templates/         # SQL templates đã validated
│
├── slot_filling/
│   ├── entity_normalizer.py        # Chuẩn hoá entity (date, amount, enum)
│   └── slot_filler.py              # Fill entity vào template
│
├── sql_generation/
│   ├── sql_prompt_builder.py       # Build 6-block prompt
│   └── llm_sql_generator.py        # Call Llama 3 via Ollama (+ warm-up)
│
├── validator/
│   ├── sql_validator.py            # Syntax check (sqlparse)
│   ├── schema_validator.py         # Table/column existence check
│   └── security_guard.py           # Block dangerous SQL
│
├── executor/
│   └── query_executor.py           # Execute + LIMIT + timeout
│
├── explain/
│   └── explain_engine.py           # Giải thích kết quả tiếng Việt
│
├── data/
│   ├── domains/
│   │   ├── registry.json           # Registry mô tả tất cả domains
│   │   ├── banking/
│   │   │   ├── semantic_profiles/
│   │   │   └── user_intent/
│   │   └── hrm/
│   │       ├── semantic_profiles/
│   │       └── user_intent/
│   ├── semantic_profiles/          # Legacy path (backward compatibility)
│   ├── user_intent/                # Legacy path (backward compatibility)
│   └── user_questions/             # Dataset câu hỏi NL
│       ├── raw/                    # File gốc (json/csv/xlsx/md)
│       ├── processed/              # Đã normalize sang JSON
│       └── test_sets/              # Bộ unit test
│
├── cache/                          # Embedding cache (intent_embeddings.pkl)
│
├── template_store/
│   ├── banking/approved_templates/
│   ├── hrm/approved_templates/
│   └── approved_templates/         # Legacy path (backward compatibility)
│
└── logs/
    ├── queries/                    # JSONL per-run query logs
    └── batch_result/               # JSON per-run batch results
```

## Cài đặt

```bash
pip install -r requirements.txt
```

Cần Ollama chạy sẵn:

```bash
ollama serve
ollama pull llama3:8b
```

## Chạy

### Interactive mode

```bash
python app.py
```

### Batch mode (từ file)

```bash
# Chạy từ file json/csv/xlsx/md
python app.py data/user_questions/raw/questions.json

# Tắt explain (nhanh hơn)
python app.py data/user_questions/test_sets/uq_test_0.md --no-explain

# Warm-up Ollama trước khi chạy
python app.py data/user_questions/raw/questions.csv --warm --no-explain

# Song song 4 threads
python app.py data/user_questions/raw/questions.json --parallel 4 --no-explain

# Force chạy trên domain cụ thể
python app.py --domain hrm
```

### CLI Options

| Flag | Mô tả |
|------|--------|
| `--no-explain` | Bỏ qua Step 8 (tiết kiệm thời gian) |
| `--parallel N` | Chạy N threads song song (batch mode) |
| `--warm` | Warm-up Ollama model trước khi chạy |
| `--domain DOMAIN_ID` | Force chạy trên domain cụ thể để debug/test |

## Demo UI

Demo UI duoc dat trong thu muc `demo_ui/` va backend API demo trong `demo_server.py`.

### 1. Cai dependency backend demo

```bash
pip install -r demo_requirements.txt
```

### 2. Chay backend demo

```bash
uvicorn demo_server:app --reload --port 8000
```

### 3. Chay frontend demo

```bash
cd demo_ui
npm install
npm run dev
```

Neu PowerShell chan `npm`, dung `npm.cmd install` va `npm.cmd run dev`.

Demo mode se:

- van chay domain router, schema router, intent detection, template retrieval va SQL generation
- show current model o thanh input, bao gom fallback `llama3` neu primary model loi
- khong truy cap DB that, Step 7 se dung local cache trong `cache/demo_execution_cache.json`
- show prompt, schema, intent, timing va SQL o debug panel ben phai

## Output format

### Console

```
User Question: Tra cứu giao dịch chuyển tiền tới số tài khoản 123 trong tháng 1
→ Domain: banking
→ Tables: ['customer_account', 'transaction']
→ Intent: tra_cứu_giao_dịch_chuyển_tiền_theo_số_tài_khoản_người_nhận
→ Entities: {'to_account_no': '123', 'start_date': '2026-01-01', 'end_date': '2026-01-31'}
→ SQL: SELECT * FROM transaction WHERE to_account_no = '123' AND trans_time BETWEEN '2026-01-01' AND '2026-01-31' LIMIT 100;
→ Validator: PASS
→ Result: 5 rows
→ Timing: schema_router=0.003s, intent_detection=0.007s, entity_extraction=0.004s, template_fill=0.001s, sql_generation=3.2s, validation=0.01s | total=3.45s
```

### Log files

Mỗi lần chạy `app.py` tạo file log riêng theo timestamp:

```
logs/
├── queries/
│   ├── 2026-03-11_09-58-39.jsonl
│   └── 2026-03-11_14-30-00.jsonl
└── batch_result/
    ├── 2026-03-11_09-58-39.json
    └── 2026-03-11_14-30-00.json
```

**Query log** (`logs/queries/{timestamp}.jsonl`) — 1 dòng / query:

```json
{
  "question": "Tra cứu giao dịch chuyển tiền tới số tài khoản 123 trong tháng 1",
  "domain": "banking",
  "candidate_domains": ["banking"],
  "tables": ["transaction", "customer_account"],
  "intent": "tra_cứu_giao_dịch_chuyển_tiền_theo_số_tài_khoản_người_nhận",
  "entities": {"to_account_no": "123", "start_date": "2026-01-01", "end_date": "2026-01-31"},
  "sql": "SELECT * FROM transaction WHERE to_account_no = '123' AND trans_time BETWEEN '2026-01-01' AND '2026-01-31' LIMIT 100",
  "validator": "PASS",
  "rows": 5,
  "timing": {"schema_router": 0.003, "intent_detection": 0.007, "sql_generation": 3.2}
}
```

**Batch result** (`logs/batch_result/{timestamp}.json`) — array tất cả kết quả của 1 lần batch.

## Performance Optimizations

| Tối ưu | Mô tả |
|--------|--------|
| Cache static resources | Schema, intents, templates load 1 lần duy nhất |
| Template-first | Nếu template fill đủ slot → skip LLM hoàn toàn |
| Singleton embedding model | Load embedding model 1 lần, reuse cho tất cả queries |
| Disk-cached embeddings | `cache/intent_embeddings.pkl` — tránh tính lại |
| Warm-up Ollama | `--warm` flag tránh cold start (~5-10s) |
| Giảm tokens + temperature | `256 tokens`, `temperature=0` → nhanh hơn 30-40% |
| `--no-explain` | Skip explain step khi benchmark |
| `--parallel N` | Chạy batch song song |

### Benchmark mục tiêu

| Step | Thời gian |
|------|-----------|
| Schema Router | ~3ms |
| Intent Detection | ~7ms |
| Entity Extraction | ~4ms |
| Template Fill | ~1ms |
| SQL Generation (LLM) | ~3-5s |
| Validation | ~10ms |
| **Total / query** | **~3-5s** |

## Cấu hình

Tất cả settings trong `config/settings.py`:

| Setting | Giá trị | Mô tả |
|---------|---------|--------|
| `LLM_BACKEND` | `"ollama"` | Backend LLM (`ollama` hoặc `transformers`) |
| `LLM_OLLAMA_MODEL` | `"llama3:8b"` | Tên model Ollama |
| `LLM_MAX_NEW_TOKENS` | `256` | Max tokens sinh ra |
| `LLM_TEMPERATURE` | `0.0` | Temperature (0 = deterministic) |
| `MAX_RETRY_ATTEMPTS` | `3` | Số lần retry tối đa |
| `QUERY_ROW_LIMIT` | `100` | LIMIT mặc định |
| `EMBEDDING_MODEL_NAME` | `multilingual-e5-base` | Model embedding cho intent/schema |
| `DOMAIN_REGISTRY_PATH` | `data/domains/registry.json` | Registry mô tả domain + db_config + metadata paths |
| `DB_HOST` | `192.168.3.7` | Default DB host fallback |
| `DB_NAME` | `ai_bank_gateway` | Default DB name fallback |
