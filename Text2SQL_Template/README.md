# Pipeline

```
User Question (VI)
        │
        ▼
[Cloud LLM API]
→ Intent Ranking
→ Entity Extraction
        │
        ▼
(Local)
Intent Profiler
        │
Template Selector
        │
Slot Filling
        │
SQL Validator
        │
Execute on DB
        │
Result + Explain
```

# Cấu trúc thư mục

```
text2sql_template/
│
├── app.py
├── config.yaml
│
├── cloud_client/
│     └── llm_api.py
│
├── intent/
│     ├── intent_index.json
│     ├── intent_profiler.py
│
├── templates/
│
├── slot_filling/
│     ├── validator.py
│     ├── normalizer.py
│
├── sql/
│     ├── sql_builder.py
│     ├── sql_validator.py
│     ├── executor.py
│
├── explain/
│     └── explain_engine.py
│
└── logs/
```