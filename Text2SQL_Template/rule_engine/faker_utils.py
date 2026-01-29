import random
import string
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from configs.dictionary import COMMON_DICTIONARY
COMMON_DICTIONARY = {}

from faker import Faker
faker = Faker('vi_VN')
class DataFaker:
    def __init__(self):
        self.use_faker = faker is not None
        self.vocab = COMMON_DICTIONARY.get("values", {})
        
        self.dict_status = self.vocab.get("STATUS", {})
        self.dict_type = self.vocab.get("TRANS_TYPE", {})
        self.dict_channel = self.vocab.get("CHANNEL", {})
        self.dict_currency = self.vocab.get("CURRENCY", {})

    def _generate_random_code(self):
        prefix = random.choice(["TYPE", "MODE", "CAT", "GRP"])
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"{prefix}_{suffix}"
    
    def _get_random_synonym(self, dictionary_group):
        if not dictionary_group: 
            if self.use_faker:
                return faker.word().upper()
            return self._generate_random_code()
                
        key = random.choice(list(dictionary_group.keys()))

        synonyms = dictionary_group[key]

        return random.choice(synonyms)

    def _generate_date(self, range_days=365):
        """Sinh ngày ngẫu nhiên trong khoảng range_days"""
        if self.use_faker:
            start_str = f'-{range_days}d'
            return faker.date_between(start_date=start_str, end_date='today').strftime('%Y-%m-%d')
        
        start = datetime.now() - timedelta(days=range_days)
        return (start + timedelta(days=random.randint(0, range_days))).strftime('%Y-%m-%d')

    def _generate_id(self, col_name):
        return str(random.randint(100000, 999999))

    def _generate_amount(self):
        """Sinh số tiền ngẫu nhiên chẵn (ví dụ: 500000, 1000000)"""
        base = random.randint(1, 100)
        multiplier = random.choice([10000, 50000, 100000, 1000000])
        return str(base * multiplier)

    def get_fake_value(self, col_name: str, role: str) -> str:
        col = col_name.lower()

        if any(x in col for x in ["status", "trang_thai", "tinh_trang"]):
            return self._get_random_synonym(self.dict_status)
        if any(x in col for x in ["curr", "ccy", "tien_te", "don_vi"]):
            return self._get_random_synonym(self.dict_currency)
        if any(x in col for x in ["channel", "kenh", "source", "receiver"]):
            return self._get_random_synonym(self.dict_channel)
        if any(x in col for x in ["trans_type", "trans_code", "service", "loai_gd", "hinh_thuc"]):
            return self._get_random_synonym(self.dict_type)
        
        if "type" in col:
            return self._get_random_synonym(self.dict_type)

        if any(x in col for x in ["date", "time"]): return self._generate_date()
        if any(x in col for x in ["amount", "bal", "fee", "limit"]): return self._generate_amount()
        if any(x in col for x in ["id", "no", "code"]): return self._generate_id(col)
        if any(x in col for x in ["channel", "kenh", "source", "receiver", "vi_du", "example"]):
            return self._get_random_synonym(self.dict_channel)
        if any(x in col for x in ["type", "loai", "code", "service", "hinh_thuc", "kieu"]):
            return self._get_random_synonym(self.dict_type)
        
        if self.use_faker: return faker.word()
        return "123"