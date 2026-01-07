"""Configuration file for Knowledge Base Microservice"""
import os
from pathlib import Path
import logging
from datetime import datetime
from typing import Optional

# =============================================================================
# DEBUG MODE
# =============================================================================
# 0 = CRITICAL: Chỉ log lỗi nghiêm trọng
# 1 = INFO: Log thông tin quan trọng (khởi động, kết quả chính)
# 2 = DEBUG: Log chi tiết để debug (tên hàm, tham số, kết quả)
# 3 = TRACE: Log tất cả (bao gồm data chi tiết)
DEBUG_MODE = 3

# =============================================================================
# LOGGING SETUP - OPTIMIZED FOR HIGH PERFORMANCE
# =============================================================================
LOG_LEVELS = {
    0: logging.CRITICAL,
    1: logging.INFO,
    2: logging.DEBUG,
    3: logging.DEBUG  # Python không có TRACE, dùng DEBUG + custom
}


class Logger:
    """High-performance logger với lazy initialization và caching

    Tối ưu cho hàng triệu requests:
    - Singleton pattern: chỉ tạo 1 instance
    - Lazy file handler: chỉ tạo khi cần
    - Cache theo giờ: không tạo lại handler mỗi request
    - Early return: skip nhanh khi debug_level không đủ
    """

    _instance: Optional['Logger'] = None

    def __new__(cls):
        """Singleton - chỉ tạo 1 instance duy nhất"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._logger: Optional[logging.Logger] = None
        self._file_handler: Optional[logging.FileHandler] = None
        self._current_log_dir: Optional[str] = None
        self._last_hour: Optional[int] = None
        self._initialized = True

    @property
    def logger(self) -> logging.Logger:
        """Lazy initialization của logger"""
        if self._logger is None:
            self._setup_logger()
        return self._logger  # type: ignore

    def _setup_logger(self):
        """Tạo logger với console handler (chỉ chạy 1 lần)"""
        self._logger = logging.getLogger("kb_api")
        self._logger.setLevel(LOG_LEVELS.get(DEBUG_MODE, logging.INFO))
        self._logger.handlers.clear()

        # Format theo debug level
        if DEBUG_MODE >= 2:
            fmt = "%(asctime)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s"
        else:
            fmt = "%(asctime)s | %(levelname)-8s | %(message)s"

        formatter = logging.Formatter(fmt, datefmt="%H:%M:%S")

        # Console handler (tạo 1 lần)
        console = logging.StreamHandler()
        console.setLevel(LOG_LEVELS.get(DEBUG_MODE, logging.INFO))
        console.setFormatter(formatter)
        self._logger.addHandler(console)

        # File handler (lazy)
        self._update_file_handler()

    def _get_log_dir(self) -> tuple[Path, int]:
        """Lấy log directory và current hour"""
        now = datetime.now()
        log_dir = Path("logs") / now.strftime("%Y") / now.strftime("%m") / now.strftime("%d")

        # Chỉ mkdir khi chưa tồn tại
        if not log_dir.exists():
            log_dir.mkdir(parents=True, exist_ok=True)

        return log_dir, now.hour

    def _update_file_handler(self):
        """Cập nhật file handler nếu đổi giờ (cached)"""
        log_dir, current_hour = self._get_log_dir()

        # Skip nếu không cần thay đổi
        if (self._last_hour == current_hour and
            self._current_log_dir == str(log_dir) and
            self._file_handler is not None):
            return

        # Đóng handler cũ
        if self._file_handler:
            self._logger.removeHandler(self._file_handler)  # type: ignore
            self._file_handler.close()

        # Tạo handler mới
        log_file = log_dir / f"app_{current_hour:02d}.log"
        self._file_handler = logging.FileHandler(log_file, encoding='utf-8')
        self._file_handler.setLevel(LOG_LEVELS.get(DEBUG_MODE, logging.INFO))

        file_fmt = "%(asctime)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s"
        self._file_handler.setFormatter(logging.Formatter(file_fmt, datefmt="%Y-%m-%d %H:%M:%S"))
        self._logger.addHandler(self._file_handler)  # type: ignore

        # Update cache
        self._current_log_dir = str(log_dir)
        self._last_hour = current_hour

    def log(self, func_name: str, message: str = "", debug_level: int = 2, **kwargs):
        """Log với context - OPTIMIZED

        Args:
            func_name: Tên hàm đang chạy
            message: Thông điệp log
            debug_level: Mức độ chi tiết (0=CRITICAL, 1=INFO, 2=DEBUG, 3=TRACE)
            **kwargs: Data bổ sung (chỉ log khi TRACE mode)
        """
        # CRITICAL: Early return - O(1) check
        if DEBUG_MODE < debug_level:
            return

        # Update file handler nếu đổi giờ
        self._update_file_handler()

        # Build message (chỉ khi thực sự log)
        msg = f"[{func_name}] {message}"
        if kwargs and DEBUG_MODE >= 3:
            msg += f" | Data: {kwargs}"

        # Log theo level
        if debug_level == 0:
            self.logger.critical(msg)
        elif debug_level == 1:
            self.logger.info(msg)
        else:
            self.logger.debug(msg)


# Singleton instance
_logger = Logger()

# Shortcut functions để backward compatible
log = _logger.logger
log_func = _logger.log

# Log startup
log_func("config", f"Loaded config | DEBUG_MODE={DEBUG_MODE}", debug_level=1)


# =============================================================================
# DATABASE SETTINGS
# =============================================================================
DB_DIR = "knowledge_base_6804"
DB_TABLE = f"{DB_DIR}.documents_6804"
# Examples table settings
EXAMPLE_SEPARATORS = ['\n', '|', '"']  # Các ký tự phân cách câu hỏi trong examples
EXAMPLES_TABLE = f"{DB_DIR}.examples"  # Bảng chứa từng câu hỏi mẫu riêng lẻ

# =============================================================================
# EMBEDDING MODEL
# =============================================================================
# Model cũ (accuracy thấp cho Vietnamese):
# EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# Model mới - multilingual-e5-large: SOTA cho multilingual semantic search
# - 1024 dimensions (vs 384 của MiniLM)
# - Trained trên 1B+ pairs, hỗ trợ Vietnamese tốt hơn
# - Yêu cầu prefix "query: " cho câu hỏi và "passage: " cho documents
# EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
EMBEDDING_MODEL = "intfloat/multilingual-e5-base"

# Weights cho hybrid search (search_text vs examples)
SEARCH_TEXT_WEIGHT = 0.3  # Weight cho search_text (document + description + keywords)
EXAMPLES_WEIGHT = 0.7     # Weight cho examples (câu hỏi mẫu) - ưu tiên cao hơn


# =============================================================================
# SEARCH SETTINGS
# =============================================================================
DEFAULT_TOP_K = 10

# =============================================================================
# HYBRID SEARCH SETTINGS (Expert-level accuracy improvement)
# =============================================================================
# Final score = SEMANTIC * semantic_weight + BM25 * bm25_weight + KEYWORD_BOOST
SEMANTIC_WEIGHT = 0.7  # Weight cho semantic search (embedding similarity)
BM25_WEIGHT = 0.2     # Weight cho BM25 keyword matching
KEYWORD_BOOST_WEIGHT = 0.1  # Weight cho keyword boosting

# BM25 parameters
BM25_K1 = 1.5  # Term frequency saturation
BM25_B = 0.75  # Length normalization


# Ambiguous words that need context - used for logging/debugging only
AMBIGUOUS_KEYWORDS = [
    "thông tin", "info", "xem", "kiểm tra", "check", "coi", "tra cứu",
    "tài khoản", "tk", "account", "acc",
]

# =============================================================================
# FILE PATHS
# =============================================================================
OUTPUT_DIR = Path("outputs")
TEMPLATE_DIR = Path("templates")

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
TEMPLATE_DIR.mkdir(exist_ok=True)



# =============================================================================
# QUERY NORMALIZATION RULES
# Chuẩn hóa query về dạng chuẩn trước khi search
# =============================================================================

# # Expand abbreviations to full form
# ABBREVIATION_EXPANSIONS = {
#     r'\btk\b': 'tài khoản',
#     r'\bgd\b': 'giao dịch',
#     r'\bstk\b': 'sổ tiết kiệm',
#     r'\blsx\b': 'lịch sử',
#     r'\bsd\b': 'số dư',
#     r'\bnh\b': 'ngân hàng',
#     r'\bck\b': 'chuyển khoản',
#     r'\bls\b': 'lịch sử',
#     r'\btt\b': 'thông tin',
#     r'\bbn\b': 'bao nhiêu',
#     r'\bbnh\b': 'bao nhiêu',
#     r'\bdc\b': 'được',
#     r'\bdk\b': 'được không',
#     r'\bacc\b': 'account tài khoản',
#     r'\binfo\b': 'thông tin',
#     r'\bct\b': 'của tôi',
#     r'\bc t\b': 'của tôi',
#     r'\btknh\b': 'tài khoản ngân hàng',
#     r'\bacc\b': 'tài khoản',
#     r'\bt.k\b': 'tài khoản',
#     r'\bdc\b': 'được',
#     r'\bd.c\b': 'được',
#     r'\bk\b': 'không',
#     r'\bt\b': 'tôi',
    
# }

# # =============================================================================
# # VIETNAMESE DIACRITICS NORMALIZATION
# # Convert Vietnamese without diacritics to standard form with diacritics
# # This is CRITICAL for matching - must run BEFORE other normalizations
# # =============================================================================
# VIETNAMESE_DIACRITICS = {
#     # Tài khoản / Account
#     r'\btai khoan\b': 'tài khoản',
#     r'\btaikhoan\b': 'tài khoản',

#     # Ngân hàng / Bank
#     r'\bngan hang\b': 'ngân hàng',
#     r'\bnganhang\b': 'ngân hàng',

#     # Số dư / Balance
#     r'\bso du\b': 'số dư',
#     r'\bsodu\b': 'số dư',

#     # Tiết kiệm / Savings
#     r'\btiet kiem\b': 'tiết kiệm',
#     r'\btietkiem\b': 'tiết kiệm',
#     r'\bso tiet kiem\b': 'sổ tiết kiệm',

#     # Giao dịch / Transaction
#     r'\bgiao dich\b': 'giao dịch',
#     r'\bgiaodich\b': 'giao dịch',
#     r'\blich su giao dich\b': 'lịch sử giao dịch',

#     # Chuyển khoản / Transfer
#     r'\bchuyen khoan\b': 'chuyển khoản',
#     r'\bchuyenkhoan\b': 'chuyển khoản',

#     # Thông tin / Information
#     r'\bthong tin\b': 'thông tin',
#     r'\bthongtin\b': 'thông tin',

#     # Của tôi / My
#     r'\bcua toi\b': 'của tôi',
#     r'\bcuatoi\b': 'của tôi',

#     # Được / Can
#     r'\bduoc\b': 'được',
#     r'\bđuoc\b': 'được',

#     # Không / No - và các biến thể miền Nam
#     r'\bkhong\b': 'không',
#     r'\bhong\b': 'không',   # Miền Nam: "hong" = "không" (không dấu)
#     r'\bhông\b': 'không',   # Miền Nam: "hông" = "không" (có dấu)
#     r'\bhk\b': 'không',
#     r'\bko\b': 'không',

#     # Lịch sử / History
#     r'\blich su\b': 'lịch sử',
#     r'\blichsu\b': 'lịch sử',

#     # Số / Number
#     r'\bso\b': 'số',

#     # Kiểm tra / Check
#     r'\bkiem tra\b': 'kiểm tra',
#     r'\bkiemtra\b': 'kiểm tra',

#     # Chi tiết / Detail
#     r'\bchi tiet\b': 'chi tiết',
#     r'\bchitiet\b': 'chi tiết',

#     # Hồ sơ / Profile
#     r'\bho so\b': 'hồ sơ',
#     r'\bhoso\b': 'hồ sơ',

#     # Cá nhân / Personal
#     r'\bca nhan\b': 'cá nhân',
#     r'\bcanhan\b': 'cá nhân',

#     # Lãi suất / Interest rate
#     r'\blai suat\b': 'lãi suất',
#     r'\blaisuat\b': 'lãi suất',

#     # Kỳ hạn / Term
#     r'\bky han\b': 'kỳ hạn',
#     r'\bkyhan\b': 'kỳ hạn',

#     # Đáo hạn / Maturity
#     r'\bdao han\b': 'đáo hạn',
#     r'\bdaohan\b': 'đáo hạn',
#     r'\bsdu\b': 'số dư',
    
# }

# # Normalize common variations to standard form
# VARIATION_NORMALIZATIONS = {
#     # English to Vietnamese
#     r'balance': 'số dư',
#     r'saving[s]?': 'tiết kiệm',
#     r'transaction[s]?': 'giao dịch',
#     r'transfer': 'chuyển khoản',
#     r'profile': 'hồ sơ cá nhân',
#     r'history': 'lịch sử',
#     r'bank': 'ngân hàng',
#     r'account': 'tài khoản',
#     r'check': 'kiểm tra',
#     r'user info': 'hồ sơ người dùng',

#     # Vietnamese variations
#     r'tiền còn': 'số dư',
#     r'tiền trong': 'số dư',
#     r'còn bao nhiêu tiền': 'số dư',
#     r'gửi tiết kiệm': 'tiết kiệm',
#     r'sổ gửi': 'sổ tiết kiệm',
#     r'thông tin cá nhân': 'hồ sơ cá nhân',
# }

# # Remove filler words that don't add meaning
# FILLER_WORDS = [
#     'ơi', 'ê', 'hey', 'yo', 'bro', 'alo',  # Gen Z prefixes
#     'real quick', 'asap', 'pls', 'plz', 'please',  # English fillers
#     'giùm', 'giúp', 'hộ', 'với',  # Vietnamese fillers (keep some)
#     'luôn', 'liền', 'ngay', 'nhanh', 'gấp',  # Urgency words
#     'vậy', 'thế', 'sao', 'rồi',  # Question fillers
# ]




