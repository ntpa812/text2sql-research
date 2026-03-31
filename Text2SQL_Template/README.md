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
   └────┬────┘                          (retry max 2: syntax → schema → logic)
        │
   ┌────┴────┐
   │  Step 6  │  Validator            ← security → syntax → schema → semantic → structure → confidence
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
├── requirements.txt                # Python dependencies
├── test.ipynb                      # Notebook thử nghiệm
│
├── config/
│   ├── settings.py                 # Settings chung + domain registry path
│   └── db_connector.py             # MySQL schema loader theo db_config
│
├── pipeline/
│   ├── runner.py                   # Orchestrator chính (domain-aware)
│   ├── retry_handler.py            # Retry strategy (2 levels)
│   ├── query_cache.py              # Hệ thống cache query
│   ├── demo_cache.py               # Demo execution cache
│   ├── test_mock.py                # Mock utilities cho testing
│   │
│   ├── domain_router/
│   │   ├── registry_loader.py      # Load domain registry
│   │   └── selector.py             # Chọn/shortlist domain bằng keyword + embedding
│   │
│   ├── schema_router/
│   │   ├── schema_loader.py        # Load semantic profiles
│   │   └── table_selector.py       # Rank bảng theo domain
│   │
│   ├── intent_detection/
│   │   ├── intent_loader.py        # Load intent dataset JSON
│   │   └── intent_ranker.py        # Ranking intent (keyword + cached embedding)
│   │
│   ├── entity_extraction/
│   │   ├── ner_local.py            # NER local (wrapper 6804_DDQ) + regex fallback
│   │   └── ner_fallback_llm.py     # Fallback: LLM entity extraction
│   │
│   ├── dataset_loader/
│   │   └── question_loader.py      # Load questions từ json/csv/xlsx/md
│   │
│   ├── template_store/
│   │   └── template_loader.py      # Load/save approved templates
│   │
│   ├── slot_filling/
│   │   ├── entity_normalizer.py    # Chuẩn hoá entity (date, amount, enum)
│   │   └── slot_filler.py          # Fill entity vào template
│   │
│   ├── sql_generation/
│   │   ├── sql_prompt_builder.py   # Build 6-block prompt
│   │   ├── llm_sql_generator.py    # Gọi LLM qua OpenAI-compatible API / Ollama
│   │   └── sql_repairer.py         # Tự động sửa SQL lỗi
│   │
│   ├── validator/
│   │   ├── sql_validator.py        # Syntax check (sqlparse)
│   │   ├── schema_validator.py     # Table/column existence check
│   │   ├── security_guard.py       # Block dangerous SQL
│   │   ├── semantic_validator.py   # Kiểm tra ngữ nghĩa SQL
│   │   ├── structure_validator.py  # Kiểm tra cấu trúc SQL
│   │   ├── confidence_scorer.py    # Tính điểm confidence
│   │   └── data_validator.py       # Validate dữ liệu trả về
│   │
│   ├── executor/
│   │   └── query_executor.py       # Execute + LIMIT + timeout
│   │
│   └── explain/
│       └── explain_engine.py       # Giải thích kết quả tiếng Việt
│
├── core/
│   └── NER/
│       ├── ner.py                  # NER model definition
│       ├── ner_inference.py        # NER inference wrapper
│       ├── vietnamese_time_parser.py # Parse thời gian tiếng Việt
│       └── stores/                 # NER data stores
│
├── evaluation/
│   ├── evaluate_pipeline.py        # Chạy gold test set qua pipeline, tính accuracy
│   ├── visualize_results.py        # Tạo biểu đồ từ kết quả evaluation
│   ├── charts/                     # Biểu đồ đã tạo (PNG)
│   └── results/                    # Kết quả evaluation (JSON)
│
├── demo/
│   ├── server.py                   # FastAPI backend demo
│   ├── requirements.txt            # Dependencies cho demo
│   └── ui/                         # Frontend demo (npm project)
│
├── data/
│   ├── domains/
│   │   ├── registry.json           # Registry mô tả tất cả domains
│   │   ├── banking/
│   │   │   ├── semantic_profiles/  # Mô tả bảng/cột cho schema routing
│   │   │   ├── user_intent/        # Intent dataset
│   │   │   └── templates/
│   │   │       └── approved_templates/  # 26 SQL templates đã validated
│   │   └── hrm/
│   │       ├── semantic_profiles/
│   │       ├── user_intent/
│   │       └── templates/
│   │           └── approved_templates/  # 15 SQL templates đã validated
│   ├── evaluation/
│   │   └── gold_test_set.jsonl     # Bộ test vàng cho pipeline evaluation
│   └── user_questions/
│       ├── processed/              # Đã normalize sang JSON
│       └── test_sets/              # Bộ unit test
│
├── cache/                          # Embedding cache (intent_embeddings.pkl), query cache
│
├── logs/
│   ├── queries/                    # JSONL per-run query logs
│   └── batch_result/               # JSON per-run batch results
│
└── reports/                        # Báo cáo phân tích
```

## Cài đặt

```bash
pip install -r requirements.txt
```

### LLM Backend

Hệ thống mặc định dùng OpenAI-compatible API (vLLM/SGLang endpoint). Nếu endpoint không khả dụng, có thể chuyển sang Ollama fallback:

```bash
# (Chỉ cần nếu dùng Ollama fallback)
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
python app.py data/user_questions/test_sets/uq_test_0.md

# Tắt explain (nhanh hơn)
python app.py data/user_questions/test_sets/uq_test_0.md --no-explain

# Warm-up LLM trước khi chạy
python app.py data/user_questions/test_sets/uq_test_0.md --warm --no-explain

# Song song 4 threads
python app.py data/user_questions/test_sets/uq_test_0.md --parallel 4 --no-explain

# Force chạy trên domain cụ thể
python app.py --domain hrm
```

### CLI Options

| Flag | Mô tả |
|------|--------|
| `--no-explain` | Bỏ qua Step 8 (tiết kiệm thời gian) |
| `--parallel N` | Chạy N threads song song (batch mode) |
| `--warm` | Warm-up LLM backend trước khi chạy |
| `--domain DOMAIN_ID` | Force chạy trên domain cụ thể để debug/test |
| `--test-mode` | Bật test mode (inject mock account) |
| `--clear-cache` | Xoá query cache trước khi chạy |

## Evaluation

Hệ thống có module evaluation đầy đủ để đo lường chất lượng pipeline.

### Chạy evaluation

```bash
# Mặc định: dùng gold test set
python evaluation/evaluate_pipeline.py

# Chỉ định gold test set khác
python evaluation/evaluate_pipeline.py --gold data/evaluation/gold_test_set.jsonl

# Không chạy explain (nhanh hơn)
python evaluation/evaluate_pipeline.py --no-explain
```

### Tạo biểu đồ

```bash
python evaluation/visualize_results.py
```

Biểu đồ được lưu tại `evaluation/charts/`:
- `component_accuracy.png` — Độ chính xác từng component
- `difficulty_breakdown.png` — Phân tích theo độ khó
- `entity_per_type.png` — Thống kê entity theo loại
- `error_distribution.png` — Phân bố lỗi
- `per_question_heatmap.png` — Heatmap từng câu hỏi

## Demo UI

Demo UI nằm trong thư mục `demo/`, backend API dùng FastAPI với SQLite mock DBs (hrm.db, banking.db).

### 1. Cài dependency backend demo

```bash
pip install -r demo/requirements.txt
```

### 2. Chạy backend demo

```bash
uvicorn demo.server:app --reload --port 8000
```

### 3. Chạy frontend demo

```bash
cd demo/ui
npm install
npm run dev
```

Nếu PowerShell chặn `npm`, dùng `npm.cmd install` và `npm.cmd run dev`.

Demo mode sẽ:

- vẫn chạy domain router, schema router, intent detection, template retrieval và SQL generation
- show current model ở thanh input, bao gồm fallback `llama3` nếu primary model lỗi
- không truy cập DB thật, Step 7 sẽ dùng local cache
- show prompt, schema, intent, timing và SQL ở debug panel bên phải

## Output format

### Console

```
User Question: Tra cứu giao dịch chuyển tiền tới số tài khoản 123 trong tháng 1
→ Domain: banking
→ Candidate Domains: ['banking']
→ Tables: ['customer_account', 'transaction']
→ Intent: tra_cứu_giao_dịch_chuyển_tiền_theo_số_tài_khoản_người_nhận
→ Entities: {'to_account_no': '123', 'start_date': '2026-01-01', 'end_date': '2026-01-31'}
→ SQL: SELECT * FROM transaction WHERE to_account_no = '123' AND trans_time BETWEEN '2026-01-01' AND '2026-01-31' LIMIT 100;
→ Validator: PASS
→ Result: 5 rows
→ Confidence: 85 (PASS)
→ Structure: 1.0
→ Cache: HIT (skip pipeline)
→ Explain: ...
→ Timing: schema_router=0.003s, intent_detection=0.007s, entity_extraction=0.004s, template_fill=0.001s, sql_generation=3.2s, validation=0.01s | total=3.45s
```

Các trường bổ sung trong output:
- **Confidence**: điểm tin cậy của SQL (PASS/LOW)
- **Structure**: điểm cấu trúc SQL, kèm danh sách vấn đề nếu có
- **Semantic warnings**: cảnh báo ngữ nghĩa (vd: điều kiện WHERE có thể sai)
- **Data validation**: kiểm tra dữ liệu trả về (DATA_ERROR nếu bất thường)
- **Cache**: hiển thị nếu kết quả lấy từ query cache
- **PASS_EMPTY**: SQL hợp lệ nhưng không có dữ liệu

### Log files

Mỗi lần chạy `app.py` tạo file log riêng theo timestamp:

```
logs/
├── queries/
│   └── 2026-03-31_13-31-16.jsonl
└── batch_result/
    └── 2026-03-31_13-31-55.json
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
  "confidence": {"score": 85, "passed": true},
  "timing": {"schema_router": 0.003, "intent_detection": 0.007, "sql_generation": 3.2}
}
```

**Batch result** (`logs/batch_result/{timestamp}.json`) — array tất cả kết quả của 1 lần batch.

## Performance Optimizations

| Tối ưu | Mô tả |
|--------|--------|
| Query cache | Cache kết quả query, trả về ngay nếu trùng câu hỏi |
| Cache static resources | Schema, intents, templates load 1 lần duy nhất |
| Template-first | Nếu template fill đủ slot → skip LLM hoàn toàn |
| Singleton embedding model | Load embedding model 1 lần, reuse cho tất cả queries |
| Disk-cached embeddings | `cache/intent_embeddings.pkl` — tránh tính lại |
| Warm-up LLM | `--warm` flag tránh cold start |
| Giảm tokens + temperature | `512 tokens`, `temperature=0` → nhanh hơn |
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
| `LLM_BACKEND` | `"openai_compatible"` | Backend LLM (`openai_compatible`, `ollama`, `transformers`) |
| `LLM_API_BASE_URL` | `"http://192.168.3.7:6805/v1"` | OpenAI-compatible API endpoint |
| `LLM_API_MODEL` | `"qwen3.5-9b"` | Model chính |
| `LLM_OLLAMA_MODEL` | `"llama3:8b"` | Model Ollama fallback |
| `LLM_MAX_NEW_TOKENS` | `512` | Max tokens sinh ra |
| `LLM_TEMPERATURE` | `0.0` | Temperature (0 = deterministic) |
| `MAX_RETRY_ATTEMPTS` | `2` | Số lần retry tối đa |
| `QUERY_ROW_LIMIT` | `100` | LIMIT mặc định |
| `QUERY_TIMEOUT_SECONDS` | `30` | Timeout query (giây) |
| `EMBEDDING_MODEL_NAME` | `multilingual-e5-base` | Model embedding cho intent/schema |
| `DOMAIN_REGISTRY_PATH` | `data/domains/registry.json` | Registry mô tả domain + db_config |
| `DOMAIN_SHORTLIST_SCORE_GAP` | `0.15` | Ngưỡng chênh lệch score domain routing |
| `DOMAIN_SHORTLIST_RELATIVE_THRESHOLD` | `0.7` | Ngưỡng tương đối để shortlist domain |
| `DOMAIN_AMBIGUITY_TOLERANCE` | `0.05` | Dung sai khi domain mơ hồ |
| `TEST_MODE` | `False` | Bật/tắt test mode |
| `TEST_ACCOUNT` | `"1234567890"` | Mock account cho test mode |
| `DB_HOST` | `192.168.3.7` | Default DB host |
| `DB_NAME` | `ai_bank_gateway` | Default DB name |
