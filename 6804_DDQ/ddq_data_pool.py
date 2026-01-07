import pymysql
import pandas as pd
# pip install tabulate  <-- Bạn cần cài thêm thư viện này để pandas xuất markdown đẹp

try:
    from config import mPs_Data_Pool
except ImportError:
    class mPs_Data_Pool:
        host = "192.168.3.7"
        port = 3306
        username = "bank-gateway"
        password = "bankgateway@123"
        database = "ai_bank_gateway" 

class DataPoolConnector:
    def __init__(self):
        self.host = mPs_Data_Pool.host
        self.port = mPs_Data_Pool.port
        self.user = mPs_Data_Pool.username
        self.password = mPs_Data_Pool.password
        self.database = mPs_Data_Pool.database 
        self.connection = None

    def connect(self):
        try:
            self.connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                cursorclass=pymysql.cursors.DictCursor
            )
        except pymysql.MySQLError as e:
            print(f"Error connecting to MariaDB: {e}")
            raise

    def execute_query(self, sql_query):
        if not self.connection:
            raise Exception("Not connected to database.")
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(sql_query)
                result = cursor.fetchall()
                return pd.DataFrame(result)
        except pymysql.MySQLError as e:
            print(f"Error executing query: {e}")
            raise

    def format_for_llm(self, df, query_description="Kết quả truy vấn"):
        """
        Định dạng linh hoạt cho mọi loại SQL query.
        Tự động chọn định dạng Table (nếu ít cột) hoặc Record (nếu nhiều cột/dữ liệu dài).
        """
        if df is None or df.empty:
            return f"### {query_description}\nKết quả: [Trống] - Không có dữ liệu được tìm thấy."

        total_rows = len(df)
        total_cols = len(df.columns)
        
        # 1. Giới hạn số lượng bản ghi để tránh tràn Context Window (Token)
        # Thông thường 20-50 dòng là ngưỡng an toàn cho LLM
        limit = 30 
        df_limited = df.head(limit)

        output = []
        output.append(f"### {query_description}")
        output.append(f"- **Tổng số dòng trong DB:** {total_rows}")
        output.append(f"- **Số cột:** {total_cols} ({', '.join(df.columns)})")
        
        if total_rows > limit:
            output.append(f"- **Lưu ý:** Chỉ hiển thị {limit} dòng đầu tiên.")
        
        output.append("\n---\n")

        # 2. CHỌN ĐỊNH DẠNG HIỂN THỊ
        # Nếu quá nhiều cột (> 8) hoặc có cột chứa text rất dài, dùng định dạng List/JSON-like sẽ tốt hơn Table
        has_long_text = df_limited.astype(str).apply(lambda s: s.str.len().max()).max() > 50

        if total_cols > 8 or has_long_text:
            # Định dạng YAML-style (Dễ đọc cho LLM khi dữ liệu phức tạp)
            output.append("DATA (Format: Record-based):\n")
            for i, row in df_limited.iterrows():
                output.append(f"Record #{i+1}:")
                for col in df.columns:
                    output.append(f"  {col}: {row[col]}")
                output.append("-" * 10)
        else:
            # Định dạng Markdown Table (Đẹp và trực quan cho dữ liệu dạng bảng số liệu)
            output.append("DATA (Format: Markdown Table):\n")
            # Cần cài: pip install tabulate
            output.append(df_limited.to_markdown(index=False))

        return "\n".join(output)

    def close(self):
        if self.connection:
            self.connection.close()

connector = DataPoolConnector()
def get_data_from_lake(sql,question_normalized, query_description="Kết quả truy vấn"):
    try:
        connector.connect()
        df = connector.execute_query(sql)
        # Định dạng dữ liệu để đưa vào Prompt cho LLM
        llm_context = connector.format_for_llm(df,query_description)

        # # In ra kết quả để copy vào Prompt
        # print("--- DỮ LIỆU ĐÃ FORMAT CHO LLM ---")
        # print(llm_context)
        # print("\n--- GỢI Ý PROMPT ---")
        # print(f"Dựa trên dữ liệu dưới đây, hãy tóm tắt tối đa 3 giao dịch lớn nhất của tài khoản {acc}:\n\n{llm_context}")
    finally:
        connector.close()
    llm_context=f"Dựa trên dữ liệu dưới đây, hãy trình bày lại kết quả của dữ liệu sau sao cho dễ đọc. ĐẶC BIỆT CHÚ Ý: CHỈ TRÌNH BÀY THÔNG TIN CÓ Ý NGHĨA VỚI END-USER:\n\n{llm_context}. **Câu hỏi**:{question_normalized}"
    return llm_context
    

# --- CHẠY THỬ ---
if __name__ == "__main__":
    connector = DataPoolConnector()
    try:
        connector.connect()

        acc = '020063535533'
        sql = f"""
        SELECT trans_id, trans_time, trans_type, amount_transfer, amount_currency, trans_status, trans_desc 
        FROM transaction 
        WHERE from_account_no = '{acc}' OR to_account_no = '{acc}' 
        ORDER BY trans_time DESC LIMIT 50;
        """

        df = connector.execute_query(sql)

        # Định dạng dữ liệu để đưa vào Prompt cho LLM
        llm_context = connector.format_for_llm(df, f"Lịch sử giao dịch của tài khoản {acc}")

        # In ra kết quả để copy vào Prompt
        print("--- DỮ LIỆU ĐÃ FORMAT CHO LLM ---")
        print(llm_context)
        print("\n--- GỢI Ý PROMPT ---")
        print(f"Dựa trên dữ liệu dưới đây, hãy tóm tắt tối đa 3 giao dịch lớn nhất của tài khoản {acc}:\n\n{llm_context}")

    finally:
        connector.close()