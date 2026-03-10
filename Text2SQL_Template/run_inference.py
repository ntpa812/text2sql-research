"""
Quick test – Llama 3 SQL generation via Ollama.
Make sure Ollama is running: `ollama serve`
And model is pulled: `ollama pull llama3`
"""

import json
from urllib.request import Request, urlopen

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "llama3:8b"

prompt = """You are an expert SQL generator for a banking database.

Your task is to write a valid SQL query based on the user question.
Only generate a SELECT query. Limit the result to 100 rows.

DATABASE SCHEMA
transaction(trans_id, trans_time, trans_type, trans_name, from_account_no, to_account_no, amount_transfer, amount_currency, trans_status, category_code)
customer_account(account_no, account_class, primary_account, status)

USER QUESTION
List all transfer transactions from account 0123456789 in January 2026

Write the final SQL query. Return ONLY the SQL query.
"""

payload = json.dumps({
    "model": MODEL,
    "prompt": prompt,
    "stream": False,
    "options": {
        "num_predict": 512,
        "temperature": 0.1,
    },
}).encode("utf-8")

req = Request(OLLAMA_URL, data=payload, headers={"Content-Type": "application/json"})

print(f"Calling Ollama ({MODEL})...")
with urlopen(req, timeout=120) as resp:
    body = json.loads(resp.read().decode("utf-8"))
    print(body.get("response", "No response"))