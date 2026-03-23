"""Test raw OpenAI-compatible API call"""
import json
from urllib.request import Request, urlopen
from config.settings import LLM_API_BASE_URL, LLM_API_KEY, LLM_API_MODEL

# Test raw API call trực tiếp
url = f"{LLM_API_BASE_URL.rstrip('/')}/chat/completions"
payload = json.dumps({
    "model": LLM_API_MODEL,
    "messages": [
        {"role": "user", "content": "Viết một SELECT query để lấy tất cả giao dịch từ bảng transaction"},
    ],
    "temperature": 0,
    "max_tokens": 256,
}).encode("utf-8")

headers = {"Content-Type": "application/json"}

print(f"[TEST] URL: {url}")
print(f"[TEST] Model: {LLM_API_MODEL}")
try:
    req = Request(url, data=payload, headers=headers)
    with urlopen(req, timeout=30) as resp:
        body = json.loads(resp.read().decode("utf-8"))
        print(f"[TEST] Response keys: {list(body.keys())}")
        print(f"[TEST] Full response:\n{json.dumps(body, indent=2, ensure_ascii=False)[:1000]}")
        
        choices = body.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "")
            print(f"\n[TEST] Extracted content (first 500 chars):\n{content[:500]}")
        else:
            print(f"[TEST] No choices in response")
except Exception as e:
    print(f"[TEST] ERROR: {e}")
    import traceback
    traceback.print_exc()
