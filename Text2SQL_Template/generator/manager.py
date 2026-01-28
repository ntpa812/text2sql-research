import os
import openai

import sys
from pathlib import Path
import pandas as pd
from datetime import datetime

root_path = str(Path(__file__).parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)

from generator.llm_usage.profiler import TableProfiler
from generator.llm_usage.sql_architect import SQLArchitect
from nlq_augmenter import NLQAugmenter

CONFIG = {
    "api_key": os.environ.get("OPENAI_API_KEY") or "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", 
    "base_url": "https://api.groq.com/openai/v1", 
    "model": "openai/gpt-oss-20b" # llama-3.3-70b-versatile
}

class LocalDDQManager:
    def __init__(self):
        self.profiler = TableProfiler()
        self.architect = SQLArchitect(
            api_key=CONFIG["api_key"], 
            base_url=CONFIG["base_url"], 
            model_name=CONFIG["model"]
        )
        self.augmenter = NLQAugmenter(
            api_key=CONFIG["api_key"], 
            base_url=CONFIG["base_url"], 
            model_name=CONFIG["model"]
        )
        
        self.output_dir = Path("generator/outputs")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_local_excel(self, table_name: str):
        print(f"[*] Đang xử lý bảng: {table_name}")
        
        profile = self.profiler.get_table_profile(table_name)
        
        sql_templates = self.architect.generate_archetypes(profile)
        
        if sql_templates:
            final_data = self.augmenter.build_dataset(sql_templates, profile)
            
            df = pd.DataFrame(final_data)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            path = self.output_dir / f"ddq_data_{table_name}_{timestamp}.xlsx"
            df.to_excel(path, index=False)
            print(f"Đã xong! File lưu tại: {path}")

if __name__ == "__main__":
    manager = LocalDDQManager()
    manager.generate_local_excel("transaction") 