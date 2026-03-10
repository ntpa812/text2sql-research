import mysql.connector

class DBSchemaLoader:

    def __init__(self):
        self.host = "192.168.3.7"
        self.port = 3306
        self.username = "bank-gateway"
        self.password = "bankgateway@123"
        self.database = "ai_bank_gateway"

    def connect(self):
        return mysql.connector.connect(
            host=self.host,
            port=self.port,
            user=self.username,
            password=self.password,
            database=self.database
        )

    def load_schema(self):
        conn = self.connect()
        cursor = conn.cursor(dictionary=True)

        query = """
        SELECT 
            TABLE_NAME,
            COLUMN_NAME,
            DATA_TYPE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s
        ORDER BY TABLE_NAME
        """

        cursor.execute(query, (self.database,))
        rows = cursor.fetchall()

        schema = {}

        for row in rows:
            table = row["TABLE_NAME"]
            column = row["COLUMN_NAME"]
            dtype = row["DATA_TYPE"]

            if table not in schema:
                schema[table] = []

            schema[table].append({
                "column": column,
                "type": dtype
            })

        cursor.close()
        conn.close()

        return schema