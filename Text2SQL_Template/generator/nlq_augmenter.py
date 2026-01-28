import json
import requests
import time
from typing import List, Dict

class NLQAugmenter:
    def __init__(self, api_key: str, base_url: str, model_name: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name

    def build_dataset(self, sql_templates: List[Dict], table_profile: Dict) -> List[Dict]:
        final_records = []
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        for template in sql_templates:
            
            sql_cmd = template.get('sql_template') or template.get('sql') or template.get('query')
            
            if not sql_cmd:
                print(f"[!] Bỏ qua 1 template do thiếu mã SQL: {template.get('logic_name', 'Unknown')}")
                continue

            prompt_content = f"Sinh 10 câu hỏi cho SQL: {template['sql_template']}"
            
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt_content}],
                "temperature": 0.8
            }

            try:
                response = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
                response.raise_for_status()
                raw_text = response.json()['choices'][0]['message']['content']
                questions_list = json.loads(raw_text.replace("```json", "").replace("```", "").strip())

                final_records.append({
                    "document": template.get('logic_name', 'Chưa đặt tên'),
                    "description": template.get('description', ''),
                    "examples": "|".join(questions_list),
                    "keyword": template.get('keywords', ''),
                    "metadata": json.dumps({"raw_text": sql_cmd}, ensure_ascii=False)
                })
                
                time.sleep(0.5) 
                
            except Exception as e:
                
                print(f"[NLQAugmenter] Error for {template['logic_name']}: {e}")
                
        return final_records