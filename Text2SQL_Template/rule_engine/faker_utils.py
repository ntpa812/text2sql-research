import random
import string
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from configs.dictionary import COMMON_DICTIONARY

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
    
    def _generate_person_name(self):
        if self.use_faker:
            return faker.name()
        return "Nguyễn Văn A"
    
    def _get_random_synonym(self, dictionary_group):
        if not dictionary_group: 
            if self.use_faker:
                return self._generate_random_code()
            return "DATA_123"
                
        key = random.choice(list(dictionary_group.keys()))
        synonyms = dictionary_group[key]
        return random.choice(synonyms)

    def _generate_date(self, range_days=365):
        if self.use_faker:
            start_str = f'-{range_days}d'
            return faker.date_between(start_date=start_str, end_date='today').strftime('%Y-%m-%d')
        
        start = datetime.now() - timedelta(days=range_days)
        return (start + timedelta(days=random.randint(0, range_days))).strftime('%Y-%m-%d')

    def _generate_id(self, col_name):
        
        col = col_name.lower()

        if "trans" in col or "ref" in col:
            return "FT" + ''.join(random.choices(string.digits, k=10))
        
        if "cif" in col or "cust" in col:
            return str(random.randint(1000000, 9999999))
            
        return str(random.randint(100, 999))
    
    def _generate_amount(self):
        base = random.randint(1, 100)
        multiplier = random.choice([10000, 50000, 100000, 1000000])
        return str(base * multiplier)

    def get_fake_value(self, col_name: str, role: str) -> str:
        col = col_name.lower()

        if any(x in col for x in ["channel", "kenh", "source", "receiver", "vi_du", "example", "input_type"]):
            return self._get_random_synonym(self.dict_channel)

        if any(x in col for x in ["type", "loai", "code", "service", "hinh_thuc", "kieu", "method", "mode"]):
            return self._get_random_synonym(self.dict_type)

        if any(x in col for x in ["status", "trang_thai", "tinh_trang"]):
            return self._get_random_synonym(self.dict_status)
        if any(x in col for x in ["curr", "ccy", "tien_te", "don_vi"]):
            return self._get_random_synonym(self.dict_currency)
        
        if any(x in col for x in ["name", "ten", "fullname", "nguoi", "chu_tk", "khach_hang"]):
            if not any(exclude in col for exclude in ["user", "file", "img", "anh", "id", "code"]):
                return self._generate_person_name()
            
        if "type" in col:
            return self._get_random_synonym(self.dict_type)

        if any(x in col for x in ["date", "time"]): return self._generate_date()
        if any(x in col for x in ["amount", "bal", "fee", "limit", "gia_tri"]): return self._generate_amount()
        if any(x in col for x in ["id", "no", "code"]): return self._generate_id(col)
    
        if role == "IDENTITY" or any(x in col for x in ["id", "ma", "no", "number", "key"]):
            if any(x in col for x in ["account", "card", "tk", "the", "cif"]):
                return "".join(random.choices(string.digits, k=random.randint(9, 14)))
            return str(random.randint(100, 999999))
            
        return str(random.randint(100, 999))
    
        # if self.use_faker: return self._generate_random_code()
        # return "123"