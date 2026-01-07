
from tatools01.ParamsBase import TactParameters, pp
AppName="6804_DDQ/DDQ_dynamic_data_query"
params_dir="./" # "6804_DDQ/data_models"
class Params_VietnameseNormalizer(TactParameters):
    """
    Tham số cho Vietnamese Text Normalizer
    Pipeline xử lý: Text Cleaning → Keyboard Typo → Teencode/Abbreviation → Diacritics → Query Rewriting
    """
    def __init__(self):
        super().__init__(ModuleName="VietnameseNormalizer", params_dir=params_dir)
        self.HD = ["Tham số cho module chuẩn hóa văn bản tiếng Việt"]

        # ==== Đường dẫn dictionary files ====
        self.dict_dir = "data_models/nlp_dictionaries"
        self.teencode_dict_path = f"{self.dict_dir}/teencode_dict.json"
        self.banking_abbr_path = f"{self.dict_dir}/banking_abbreviations.json"
        self.keyboard_typo_path = f"{self.dict_dir}/keyboard_typos.json"
        self.stopwords_path = f"{self.dict_dir}/stopwords_vi.json"

        # ==== Stage 1: Text Cleaning ====
        self.enable_text_cleaning = True
        self.remove_emoji = True
        self.normalize_unicode = True  # NFC normalization
        self.normalize_whitespace = True
        self.lowercase = True

        # ==== Stage 2: Keyboard Typo Correction ====
        self.enable_keyboard_typo = True
        self.telex_correction = True  # nhuxng → những, tieenf → tiền
        self.vni_correction = True    # nhu7ng → những

        # ==== Stage 3: Teencode & Abbreviation Expansion ====
        self.enable_teencode_expansion = True
        self.enable_banking_abbreviation = True  # CCTG → chứng chỉ tiền gửi
        self.min_word_length_for_abbr = 2  # Bỏ qua từ ngắn hơn 2 ký tự

        # ==== Stage 4: Diacritics Restoration ====
        self.enable_diacritics_restoration = False  # Tắt mặc định vì cần model
        self.diacritics_model_path = ""  # Path to vn-accent-restorer model
        self.diacritics_confidence_threshold = 0.7

        # ==== Stage 5: Query Rewriting (for RAG) ====
        self.enable_query_rewriting = False  # Tắt mặc định vì cần LLM
        self.query_rewrite_llm_url = "http://192.168.3.7:6801/v1/chat/completions"
        self.query_rewrite_model = "openai/gpt-oss-20b"
        self.query_rewrite_max_tokens = 128

        # ==== Stopwords cho BM25 ====
        self.use_extended_stopwords = True
        self.custom_stopwords = []  # Thêm stopwords tùy chỉnh

        # ==== Semantic Cache (cho Query Rewriting) ====
        self.enable_semantic_cache = False
        self.cache_similarity_threshold = 0.92
        self.cache_max_size = 10000
        self.cache_ttl_hours = 24

        # ==== Logging ====
        self.log_normalized_queries = True
        self.log_level = "INFO"
        
        self.web_title="Dynamic Data Query (DDQ) Intents"
        
        self.load_then_save_to_yaml(file_path=f"{AppName}.yml")

class Params_ner(TactParameters):
    def __init__(self):
        super().__init__(ModuleName="ner_inference", params_dir=params_dir)
        self.HD = ["Chương trình NER"]
        self.Ner_Key_Mapping={
            "Loại_tiền_tệ": "amount_currency",
            "Loại_tài_khoản": "Loại_tài_khoản",
            "Ngày_giao_dịch": "trans_time",
            "Số_tài_khoản": "account_number",
            "Tên_tài_khoản": "Tên_tài_khoản",
            "bank": "bank",
            "giờ_giao_dịch": "giờ_giao_dịch",
            "kênh_giao_dịch": "request_channel",
            "loại_giao_dịch": "trans_type",
            "nội_dung_chuyển_tiền": "nội_dung_chuyển_tiền",
            "phí_giao_dịch": "fee_amount",
            "status": "status",
            "số_giao_dịch": "trans_ref_no",
            "số_tiền": "amount_transfer",
        }
        self.ner_model_path = "/home/javis-ai/Javis_AI_UAT/Javis_AI_DEMO/6804_DDQ/data_models/ner_model/NER_New_Model_14_entities_running"
        self.load_then_save_to_yaml(file_path=f"{AppName}.yml")

class Params_Data_Pool(TactParameters):
    def __init__(self):
        super().__init__(ModuleName="DDQ_Data_Pool", params_dir=params_dir)
        self.HD = ["Chương trình DDQ"]
        
        # self.url= "jdbc:mariadb://192.168.3.7:3306"
        self.host = "192.168.3.7"
        self.port = 3306
        self.username= "bank-gateway"
        self.password= "bankgateway@123"
        self.database= "ai_bank_gateway"
        self.load_then_save_to_yaml(file_path=f"{AppName}.yml")

class Params_PreProcessing(TactParameters):
    def __init__(self):
        super().__init__(ModuleName="PreProcessing", params_dir=params_dir)
        self.HD = ["Chương trình PreProcessing"]  
        self.fix_Vietnamese_Errors_URL='http://192.168.3.7:6803/api/fix_Vietnamese_Errors'   
        self.load_then_save_to_yaml(file_path=f"{AppName}.yml")

mPs_VietnameseNormalizer = Params_VietnameseNormalizer()
mPs_ner = Params_ner()
mPs_Data_Pool = Params_Data_Pool()
mPs_PreProcessing = Params_PreProcessing()

