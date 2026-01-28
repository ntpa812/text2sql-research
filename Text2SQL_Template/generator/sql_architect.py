import json
import requests
from typing import List, Dict

class SQLArchitect:
    def __init__(self, api_key: str, base_url: str, model_name: str):
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.model_name = model_name

    def generate_archetypes(self, table_profile: Dict) -> List[Dict]:
        prompt_content = f"""Dựa trên profile sau, sinh danh sách SQL Template: {table_profile.get('summary', '')}
                
                --- QUY TẮC BẮT BUỘC ---
            
            1. Trả về đúng định dạng JSON List.
            2. Tên các thuộc tính trong mỗi Object PHẢI CHÍNH XÁC là: 
               "logic_name", "description", "sql_template", "required_entities", "keywords".
            3. KHÔNG ĐƯỢC thay đổi tên "sql_template" thành bất kỳ tên nào khác.
            ...
            """
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "Bạn là chuyên gia SQL ngân hàng. Chỉ trả ra JSON List."},
                {"role": "user", "content": prompt_content}
            ],
            "temperature": 0.2
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
            raw_content = response.json()['choices'][0]['message']['content']
            clean_json = raw_content.replace("```json", "").replace("```", "").strip()
            return json.loads(clean_json)
        except Exception as e:
            print(f"[SQLArchitect] Error: {e}")
            return []