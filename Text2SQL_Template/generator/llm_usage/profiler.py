import pymysql
import pandas as pd
import json
import sys
from pathlib import Path

root_path = str(Path(__file__).parent.parent)
if root_path not in sys.path:
    sys.path.append(root_path)
    
    
from ddq_data_pool import connector
from ddq_intent_config import log_func

class TableProfiler:
    def __init__(self):
        self.connector = connector

    def get_table_profile(self, table_name: str):
        log_func("TableProfiler", f"Starting profile for table: {table_name}", debug_level=1)
        
        try:
            self.connector.connect()
            
            columns_info = self.connector.execute_query(f"DESCRIBE {table_name}")
            
            profile = {
                "table_name": table_name,
                "columns": [],
                "primary_keys": [],
                "summary": ""
            }

            for _, col in columns_info.iterrows():
                col_name = col['Field']
                col_type = col['Type'].lower()
                is_pk = col['Key'] == 'PRI'
                
                if is_pk:
                    profile["primary_keys"].append(col_name)

                stats = self._analyze_column_data(table_name, col_name, col_type)
                
                col_profile = {
                    "name": col_name,
                    "type": col_type,
                    "role": stats['role'],
                    "distinct_count": stats['distinct_count'],
                    "sample_values": stats['samples'],
                    "range": stats['range'] 
                }
                profile["columns"].append(col_profile)

            profile["summary"] = self._generate_text_summary(profile)
            
            log_func("TableProfiler", f"Profile completed for {table_name}", debug_level=1)
            return profile

        finally:
            self.connector.close()

    def _analyze_column_data(self, table_name, col_name, col_type):
        res = self.connector.execute_query(f"SELECT COUNT(DISTINCT `{col_name}`) as c FROM `{table_name}`")
        distinct_count = int(res.iloc[0]['c']) if not res.empty else 0

        role = "DIMENSION"
        samples = []
        val_range = None

        if "int" in col_type or "decimal" in col_type or "float" in col_type or "double" in col_type:
            if distinct_count > 20: 
                role = "MEASURE"
                r_res = self.connector.execute_query(f"SELECT MIN(`{col_name}`) as mn, MAX(`{col_name}`) as mx FROM `{table_name}`")
                val_range = (r_res.iloc[0]['mn'], r_res.iloc[0]['mx'])
            else:
                role = "DIMENSION"
        
        elif "date" in col_type or "time" in col_type:
            role = "TIME"
            r_res = self.connector.execute_query(f"SELECT MIN(`{col_name}`) as mn, MAX(`{col_name}`) as mx FROM `{table_name}`")
            val_range = (str(r_res.iloc[0]['mn']), str(r_res.iloc[0]['mx']))

        if role == "DIMENSION" and distinct_count > 0:
            s_res = self.connector.execute_query(f"SELECT DISTINCT `{col_name}` FROM `{table_name}` WHERE `{col_name}` IS NOT NULL LIMIT 8")
            samples = s_res[col_name].tolist()

        return {
            "role": role,
            "distinct_count": distinct_count,
            "samples": samples,
            "range": val_range
        }

    def _generate_text_summary(self, profile):
        summary = [f"Table: {profile['table_name']}"]
        
        target_columns = profile['columns'][:20]
        
        # for col in profile['columns']:
        #     line = f"- Col: {col['name']} ({col['type']}) | Role: {col['role']}"
        #     if col['sample_values']:
        #         line += f" | Samples: {', '.join(map(str, col['sample_values']))}"
        #     if col['range']:
        #         line += f" | Range: {col['range'][0]} to {col['range'][1]}"
        #     summary.append(line)
        
        for col in target_columns:

            samples = col['sample_values'][:3]
            line = f"- Col: {col['name']} ({col['type']}) | Role: {col['role']}"
            if samples:
                line += f" | Samples: {', '.join(map(str, samples))}"
            summary.append(line)
        
        if len(profile['columns']) > 20:
            summary.append(f"... và {len(profile['columns']) - 20} cột khác đã được lược bỏ.")
        
        return "\n".join(summary)

if __name__ == "__main__":
    profiler = TableProfiler()
    table_profile = profiler.get_table_profile("transaction")
    
    print("--- TABLE PROFILE FOR LLM ---")
    print(table_profile["summary"])
    
    with open("table_profile.json", "w", encoding="utf-8") as f:
        json.dump(table_profile, f, ensure_ascii=False, indent=4)