# Banking Text2SQL Pipeline

Hệ thống chuyển đổi câu hỏi tiếng Việt về giao dịch ngân hàng thành SQL, sử dụng Llama 3 (8B) qua Ollama.

## Luồng xử lý (8 bước)

```
User Question (Vietnamese)
        │
   ┌────┴────┐
   │  Step 1  │  Schema Router        ← chọn bảng liên quan (keyword + embedding)
   └────┬────┘
        │
   ┌────┴────┐
   │  Step 2  │  Intent Detection     ← nhận diện intent từ dataset (keyword/embedding)
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
   └────┬────┘
        │
   ┌────┴────┐
   │  Step 6  │  Validator            ← security → syntax → schema check
   └────┬────┘                          (retry max 3: syntax → schema → logic)
        │
   ┌────┴────┐
   │  Step 7  │  Execute on DB        ← parameterized query, LIMIT 100, timeout
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
├── test_pipeline.py                # Quick test pipeline steps
│
├── config/
│   ├── settings.py                 # Tất cả settings (DB, LLM, paths, embedding)
│   └── db_connector.py             # MySQL schema loader
│
├── pipeline/
│   ├── pipeline_runner.py          # Orchestrator chính (8 steps + per-step timing)
│   └── retry_handler.py            # Retry strategy (3 levels)
│
├── schema_router/
│   ├── schema_loader.py            # Load semantic profiles
│   └── table_selector.py           # Chọn bảng (keyword + embedding singleton)
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
│   ├── semantic_profiles/          # JSON schema cho mỗi bảng
│   ├── user_intent/                # Intent dataset (86 intents, 1000+ examples)
│   └── user_questions/             # Dataset câu hỏi NL
│       ├── raw/                    # File gốc (json/csv/xlsx/md)
│       ├── processed/              # Đã normalize sang JSON
│       └── test_sets/              # Bộ unit test
│
├── cache/                          # Embedding cache (intent_embeddings.pkl)
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
```

### CLI Options

| Flag | Mô tả |
|------|--------|
| `--no-explain` | Bỏ qua Step 8 (tiết kiệm thời gian) |
| `--parallel N` | Chạy N threads song song (batch mode) |
| `--warm` | Warm-up Ollama model trước khi chạy |

## Output format

### Console

```
User Question: Tra cứu giao dịch chuyển tiền tới số tài khoản 123 trong tháng 1
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
| `DB_HOST` | `192.168.3.7:3306` | MySQL server |
| `DB_NAME` | `ai_bank_gateway` | Database name |
