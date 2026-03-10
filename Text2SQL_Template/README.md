# Banking Text2SQL Pipeline

## Luồng xử lý

```
User Question (Vietnamese)
        │
        ▼
Schema Router          ← chọn bảng liên quan (keyword + embedding)
        │
        ▼
Intent Detection       ← nhận diện intent từ dataset (keyword/embedding)
        │
        ▼
Template Retrieval     ← lấy approved SQL template cho intent
        │
        ▼
Entity Extraction      ← NER local (6804_DDQ) + fallback LLM
        │
        ▼
Slot Filling           ← normalize entities + fill vào template
        │
        ▼
SQL Generation         ← LLM viết SQL (6-block prompt: schema + intent + entity + template)
        │
        ▼
Validator              ← security → syntax → schema check
        │
        ├── FAIL → Retry Pipeline (max 3: syntax → schema → logic)
        │
        ▼
Execute on DB          ← parameterized query, LIMIT 100, timeout
        │
        ▼
Explain Engine         ← giải thích kết quả bằng tiếng Việt
```

## Cấu trúc thư mục

```
Text2SQL_Template/
│
├── app.py                          # Entry point
├── config/
│   ├── settings.py                 # Tất cả settings (DB, LLM, paths)
│   └── db_connector.py             # MySQL schema loader
│
├── pipeline/
│   ├── pipeline_runner.py          # Orchestrator chính
│   └── retry_handler.py            # Retry strategy (3 levels)
│
├── schema_router/
│   ├── schema_loader.py            # Load semantic profiles
│   └── table_selector.py           # Chọn bảng (keyword + embedding)
│
├── intent_detection/
│   ├── intent_loader.py            # Load intent dataset JSON
│   └── intent_ranker.py            # Ranking intent (keyword + embedding)
│
├── entity_extraction/
│   ├── ner_local.py                # NER local (wrapper 6804_DDQ)
│   └── ner_fallback_llm.py         # Fallback: LLM entity extraction
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
│   └── llm_sql_generator.py        # Call LLM sinh SQL
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
│   └── user_intent/                # Intent dataset (JSON + XLSX)
│
├── models/
│   └── mars-sql/                   # LLM model (4-bit quantized)
│
└── logs/                           # Query logs (JSONL per day)
│
├── explain/
│     └── explain_engine.py
│
└── logs/

```

## Chạy

```bash
python app.py
```

## Ví dụ

```
User Question: Tra cứu giao dịch chuyển tiền tới số tài khoản 123 trong tháng 1

→ Schema Router: [transaction, customer_account]
→ Intent: tra_cu_giao_dch_chuyn_tin_theo_s_ti_khon_ngi_nhn
→ Entities: {"to_account_no": "123", "start_date": "2026-01-01", "end_date": "2026-01-31"}
→ SQL: SELECT * FROM transaction WHERE to_account_no = '123' AND trans_time BETWEEN '2026-01-01' AND '2026-01-31' LIMIT 100;
→ Validator: PASS
→ Result: 5 rows
```