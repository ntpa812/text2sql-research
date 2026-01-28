import random
from datetime import datetime, timedelta
from faker import Faker

faker = Faker('vi_VN')

class DataFaker:
    def __init__(self):
        
        self.use_faker = faker is not None

    def _generate_date(self, range_days=365):

        if self.use_faker:

            return faker.date_between(start_date='-1y', end_date='today').strftime('%Y-%m-%d')
        else:
            # Fallback
            start = datetime.now() - timedelta(days=range_days)
            return (start + timedelta(days=random.randint(0, range_days))).strftime('%Y-%m-%d')

    def _generate_name(self):

        if self.use_faker:
            return faker.name()
        return f"Nguyễn Văn {random.choice(['A', 'B', 'Hùng', 'Dũng', 'Lan'])}"

    def _generate_id(self, col_name):

        col_lower = col_name.lower()
        
        if "card" in col_lower:
            # Sinh fake thẻ Visa/Master bắt đầu bằng 4 hoặc 5
            prefix = random.choice(['4', '5'])
            rest = ''.join([str(random.randint(0, 9)) for _ in range(15)])
            return prefix + rest
        
        # 2. Số tài khoản 9-14 số
        if "account" in col_lower or "acct" in col_lower or "stk" in col_lower:
            return str(random.randint(1000000000, 9999999999999))
            
        # 3. CIF (Customer Info File) 6-8 số
        if "cif" in col_lower:
            return str(random.randint(100000, 99999999))

        # 4. Mã giao dịch có chữ và số
        if "ref" in col_lower or "trans" in col_lower:
            prefix = "FT" # Funds Transfer
            return prefix + str(random.randint(100000000, 999999999))
            
        # Mặc định ID số nguyên ngắn
        return str(random.randint(1000, 99999))

    def _generate_amount(self):

        base = random.randint(1, 500)
        multiplier = random.choice([10000, 50000, 100000])
        return str(base * multiplier)

    def get_fake_value(self, col_name: str, role: str, enum_values: list = None) -> str:
        
        col_lower = col_name.lower()

        # Ưu tiên lấy từ danh sách Enum (nếu có)
        # Ví dụ: trans_status -> ['SUCCESS', 'FAIL']
        if enum_values and len(enum_values) > 0:
            return str(random.choice(enum_values))

        # Dựa vào Suffix tên cột
        if any(x in col_lower for x in ["_date", "_time", "dob", "created_at"]):
            return self._generate_date()
        
        if any(x in col_lower for x in ["_name", "fullname", "customer_name"]):
            return self._generate_name()
            
        if "_mail" in col_lower:
            return faker.email() if self.use_faker else "user@example.com"
            
        if "_phone" in col_lower:
            return faker.phone_number() if self.use_faker else "0901234567"

        if any(x in col_lower for x in ["_addr", "address", "location"]):
            return faker.address().replace('\n', ', ') if self.use_faker else "Hà Nội"

        # Dựa vào Role của cột
        if role == "METRIC" or any(x in col_lower for x in ["_amount", "_bal", "_limit", "_fee"]):
            return self._generate_amount()

        if role == "IDENTITY" or any(x in col_lower for x in ["_id", "_code", "_no"]):
            return self._generate_id(col_name)

        # Mặc định trả về giá trị giả
        if self.use_faker:
            return faker.word()
        return "123"

# quick test
if __name__ == "__main__":
    fake = DataFaker()
    print("Test date:", fake.get_fake_value("create_date", "TEMPORAL"))
    print("Test name:", fake.get_fake_value("full_name", "ATTRIBUTE"))
    print("Test acc:", fake.get_fake_value("account_number", "IDENTITY"))
    print("Test amt:", fake.get_fake_value("trans_amount", "METRIC"))