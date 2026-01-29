import re

class SQLValidator:
    def __init__(self, schema_cols: list):
        self.valid_cols = set(col.lower() for col in schema_cols)

    def verify_generator_output(self, question: str, sql: str, expected_entity: str) -> bool:
        """
        Check 1: Entity trong câu hỏi có nằm trong SQL không?
        """
        if expected_entity not in sql:
            return False 
        return True

    def verify_parser_output(self, generated_sql: str) -> dict:
        """
        Check 2: SQL có dùng đúng tên cột trong Schema không?
        """
        # Trích xuất tất cả từ sau WHERE, SELECT, GROUP BY... (Simplified regex)
        # Đây là logic đơn giản, thực tế cần thư viện sqlparse
        tokens = re.findall(r'\b[a-z_][a-z0-9_]*\b', generated_sql.lower())
        
        unknown_cols = []
        keywords = ["select", "from", "where", "and", "sum", "between", "order", "by", "desc", "asc"]
        
        for token in tokens:
            if token not in keywords and token not in self.valid_cols:
                # Nếu không phải từ khóa SQL và không phải tên cột -> Nghi ngờ
                # (Lưu ý: Tên bảng cũng cần được whitelist)
                unknown_cols.append(token)
                
        if unknown_cols:
            return {"valid": False, "error": f"Cột lạ: {unknown_cols}"}
            
        return {"valid": True}