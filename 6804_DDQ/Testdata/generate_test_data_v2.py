"""
Generate test data variations for Vietnamese banking questions - V2 EXPANDED
Applies 100+ variation methods to create tens of thousands of test questions
"""
import csv
import random
import re
from typing import List, Set
from itertools import combinations

# =============================================================================
# EXPANDED VARIATION RULES - 100+ METHODS
# =============================================================================

# Nhóm 1: Đại từ nhân xưng (15 biến thể)
PRONOUNS_MAP = {
    "của tôi": ["của mình", "của em", "của tui", "của t", "của anh", "của chị",
                "tôi", "mình", "em", "tui", "", "của tao", "tao", "của cháu", "cháu"],
    "tôi": ["mình", "em", "tui", "t", "anh", "chị", "", "tao", "cháu", "con"],
    "cho tôi": ["cho mình", "cho em", "cho tui", "giùm tôi", "giúp tôi", "hộ tôi",
                "cho t", "giùm mình", "giúp mình", "cho anh", "cho chị"],
    "của tôi": ["", "của mình", "mình", "tôi", "của em", "em"],
}

# Nhóm 2: Động từ (20+ biến thể mỗi loại)
VERBS_MAP = {
    "xem": ["kiểm tra", "check", "coi", "tra cứu", "xem xét", "show", "hiển thị",
            "mở", "đọc", "dò", "tìm", "lấy", "xem qua", "xem thử", "cek", "ck"],
    "cho biết": ["cho xem", "cho hay", "nói cho biết", "thông báo", "báo",
                 "cho tôi biết", "nói", "kể", "liệt kê", "đưa ra"],
    "muốn": ["cần", "mong", "thích", "", "đang cần", "rất cần", "cần phải"],
    "kiểm tra": ["check", "xem", "tra", "dò", "coi", "verify", "test", "kiem tra"],
    "liệt kê": ["list", "show", "đưa ra", "cho xem", "hiển thị", "kể ra"],
}

# Nhóm 3: Từ vựng đồng nghĩa EXPANDED (30+ từ)
SYNONYMS_MAP = {
    # Tài khoản
    "tài khoản": ["TK", "account", "acc", "tk", "tài khoản ngân hàng", "tài khoản NH",
                  "acc ngân hàng", "account bank", "tknh", "tài khoản bank"],
    "tài khoản của tôi": ["TK của tôi", "acc của tôi", "tài khoản", "TK", "acc tôi", "tk tôi"],

    # Số dư
    "số dư": ["balance", "tiền", "số tiền", "dư", "số dư hiện có", "money",
              "tiền trong TK", "số dư TK", "balance TK", "tiền còn lại"],
    "số dư hiện tại": ["balance hiện tại", "tiền hiện có", "số dư lúc này", "số dư bây giờ",
                       "tiền còn", "balance now", "current balance"],
    "số dư khả dụng": ["available balance", "tiền khả dụng", "số tiền có thể dùng",
                       "balance available", "tiền dùng được"],

    # Chi tiết/Thông tin
    "chi tiết": ["thông tin", "info", "details", "detail", "thông tin chi tiết", ""],
    "thông tin": ["info", "chi tiết", "data", "details", "thông tin chi tiết"],

    # Ngân hàng
    "ngân hàng": ["NH", "bank", "ngân hàng Proton", "", "Proton", "proton bank"],

    # Thời gian
    "hiện tại": ["bây giờ", "lúc này", "hiện giờ", "hiện", "", "now", "hôm nay", "giờ này"],
    "gần đây": ["mới đây", "recently", "vừa rồi", "hôm qua", "tuần này", "tháng này"],

    # Số lượng
    "bao nhiêu": ["bn", "bnh", "là gì", "sao", "thế nào", "bằng bao nhiêu", "là bao nhiêu",
                  "được bao nhiêu", "có bao nhiêu", "mấy", "bao nhiu"],
    "còn": ["đang có", "có", "đang còn", "hiện còn", "vẫn còn", "còn lại"],
    "tất cả": ["all", "toàn bộ", "hết", "đầy đủ", "full", "tất", "hết thảy"],

    # Tiết kiệm
    "sổ tiết kiệm": ["STK", "tiết kiệm", "sổ TK", "saving", "sổ", "tài khoản tiết kiệm",
                     "savings", "sổ gửi", "khoản tiết kiệm", "tktk", "saving account"],
    "tiết kiệm": ["TK", "saving", "gửi tiết kiệm", "tiền gửi", "savings"],

    # Giao dịch
    "giao dịch": ["GD", "transaction", "gd", "lịch sử GD", "trans", "giao dịch ngân hàng"],
    "lịch sử giao dịch": ["history GD", "LS giao dịch", "transaction history", "sao kê",
                          "lịch sử GD", "GD history", "các giao dịch"],
    "lịch sử": ["history", "LS", "ls", "quá khứ", "trước đây"],
    "chuyển tiền": ["chuyển khoản", "CK", "transfer", "chuyển", "ck tiền", "chuyển $"],
    "chuyển khoản": ["CK", "transfer", "chuyển tiền", "ck", "chuyển", "banking transfer"],

    # Thông tin cá nhân
    "thông tin cá nhân": ["profile", "hồ sơ", "thông tin", "info cá nhân", "personal info",
                          "thông tin người dùng", "user profile", "info user"],
    "hồ sơ": ["profile", "hồ sơ cá nhân", "thông tin", "info"],

    # Danh sách
    "danh sách": ["list", "ds", "các", "những", "liệt kê"],
}

# Nhóm 4: Prefix EXPANDED (40+)
PREFIXES = [
    # Trống
    "",
    # Yêu cầu lịch sự
    "Cho tôi ", "Tôi muốn ", "Tôi cần ", "Giúp tôi ", "Làm ơn ", "Vui lòng ",
    "Xin ", "Xin vui lòng ", "Xin hãy ", "Phiền bạn ", "Nhờ bạn ",
    # Yêu cầu thân mật
    "Cho mình ", "Mình muốn ", "Mình cần ", "Giùm mình ", "Giúp mình ",
    "Cho em ", "Em muốn ", "Em cần ", "Giúp em ",
    "Cho tui ", "Tui muốn ", "Tui cần ",
    # Hỏi
    "Có thể ", "Được không nếu ", "Bạn có thể ", "Có cách nào ",
    "Làm sao để ", "Làm thế nào để ", "Cách nào để ",
    # Gấp gáp
    "Nhanh ", "Gấp ", "Khẩn ",
    # Thân mật/Gen Z
    "Ê ", "Ơi ", "Hey ", "Yo ", "Bro ", "Alo ",
    # Mở đầu khác
    "Show ", "Check ", "Cho xem ", "Mở ", "Lấy ",
]

# Nhóm 5: Suffix EXPANDED (50+)
SUFFIXES = [
    # Trống và dấu câu
    "", "?", "!", ".",
    # Nhờ vả
    " được không", " được không?", " được hông", " dc ko", " đc k", " dk", " dc hk",
    " có được không", " có thể không", " được chứ",
    # Thân mật
    " nhé", " nha", " hen", " nghen", " nhen", " ha", " hén",
    " với", " đi", " cái", " xíu", " tí", " chút",
    " luôn", " liền", " ngay", " nhanh", " gấp",
    # Lịch sự
    " ạ", " dạ", " vâng", " nhé ạ", " nha ạ", " với ạ",
    " giùm", " giúp", " hộ", " giùm với", " giúp với",
    # Gen Z
    " real quick", " asap", " pls", " plz", " please",
    # Kết hợp
    " nha bạn", " nhé bạn", " với bạn", " ạ bạn",
    " đi nào", " coi", " cái coi", " thử", " xem thử",
    " vậy", " thế", " sao", " rồi",
]

# Nhóm 6: Lỗi chính tả phổ biến EXPANDED
TYPOS_MAP = {
    "tài khoản": ["tai khoan", "tai khoản", "tài khon", "tài khoăn", "tài koản",
                  "tai khản", "tài khảon", "tai khỏan", "taikhoan", "tai khoàn"],
    "số dư": ["so du", "sô dư", "số du", "so dư", "sodu", "số dừ", "sô du"],
    "kiểm tra": ["kiem tra", "kiêm tra", "kiểm tra", "kiemtra", "kiem trả", "kiểm trà"],
    "chi tiết": ["chi tiet", "chy tiết", "chi tiêt", "chitiet", "chi tiêt", "chi tíêt"],
    "giao dịch": ["giao dich", "giao dịhc", "gd", "giaodich", "giao dich", "giao địch"],
    "tiết kiệm": ["tiet kiem", "tiêt kiệm", "tiet kiệm", "tietkiem", "tiết kiêm", "tiêt kiêm"],
    "lịch sử": ["lich su", "lịch sừ", "lich sử", "lichsu", "lịch su", "lịh sử"],
    "chuyển khoản": ["chuyen khoan", "chuyên khoản", "chuyển khon", "chuyenkhoan", "chuyển koản"],
    "thông tin": ["thong tin", "thông tìn", "thongtin", "thông tin", "thong tín"],
    "ngân hàng": ["ngan hang", "ngân hàg", "nganhang", "ngân hang", "ngan hàng"],
    "hiện tại": ["hien tai", "hiện tại", "hientai", "hiên tại", "hiện tài"],
    "danh sách": ["danh sach", "danhsach", "danh sách", "danh sach", "danh sáh"],
}

# Nhóm 7: Cách nói vùng miền
REGIONAL = {
    "xem": ["coi", "coai"],  # Miền Nam
    "được không": ["được hông", "đc hk", "dc hong"],  # Miền Nam
    "gì": ["chi", "gì vậy"],  # Miền Trung/Nam
    "như thế nào": ["làm sao", "sao", "ra sao"],
    "bao nhiêu": ["bao nhiu", "mấy"],
}

# Nhóm 8: Code-mixing (Việt-Anh)
CODE_MIX = {
    "xem": ["check", "view", "show"],
    "tài khoản": ["account", "acc"],
    "số dư": ["balance", "money"],
    "lịch sử": ["history"],
    "giao dịch": ["transaction", "trans"],
    "tiết kiệm": ["saving", "savings"],
    "thông tin": ["info", "information"],
    "danh sách": ["list"],
    "chi tiết": ["detail", "details"],
    "chuyển khoản": ["transfer"],
}

# Nhóm 9: Viết tắt teen/chat
ABBREVIATIONS = {
    "tài khoản": ["tk", "TK", "t.k", "T.K"],
    "số dư": ["sd", "SD", "s.d"],
    "giao dịch": ["gd", "GD", "g.d"],
    "tiết kiệm": ["tk", "TK", "stk", "STK"],
    "lịch sử": ["ls", "LS", "l.s"],
    "chuyển khoản": ["ck", "CK", "c.k"],
    "ngân hàng": ["nh", "NH", "n.h"],
    "thông tin": ["tt", "TT", "t.t"],
    "được không": ["đk", "dc k", "dk", "dc ko", "đc k"],
    "bao nhiêu": ["bn", "bnh", "b.n"],
    "của tôi": ["của t", "c t", "ct"],
}

# =============================================================================
# EXPANDED BASE QUESTIONS - 25+ PER API
# =============================================================================

API_QUESTIONS = {
    "getAccountDetail": [
        # Original 10
        "Xem chi tiết tài khoản của tôi",
        "Số dư tài khoản hiện tại là bao nhiêu",
        "Tài khoản của tôi thuộc loại nào",
        "Cho tôi biết chi nhánh mở tài khoản",
        "Kiểm tra trạng thái tài khoản ngân hàng của tôi",
        "Tôi muốn xem tên sản phẩm và loại tiền của tài khoản",
        "Số tài khoản và số dư hiện tại của tôi là gì",
        "Cho biết hạn mức thấu chi của tài khoản",
        "Tài khoản của tôi còn đang hoạt động không",
        "Xem thông tin chi tiết tài khoản ngân hàng",
        # Expanded - Số dư focus
        "Tài khoản còn tiền không",
        "Số dư khả dụng là bao nhiêu",
        "Kiểm tra tiền trong tài khoản",
        "Xem số dư",
        "TK của tôi",
        "Còn bao nhiêu tiền trong tài khoản",
        "Tiền trong TK còn bao nhiêu",
        "Check số dư tài khoản",
        "Tôi còn bao nhiêu tiền",
        "Balance tài khoản",
        # Expanded - Thông tin TK
        "Thông tin tài khoản",
        "Chi tiết TK",
        "Xem account của tôi",
        "Loại tài khoản của tôi là gì",
        "Tài khoản mở ngày nào",
        "TK của tôi thuộc chi nhánh nào",
        "Xem số tài khoản của tôi",
        "Tài khoản của tôi là số mấy",
        "Account number của tôi",
        "Mã tài khoản của tôi",
    ],

    "getAllSavings": [
        # Original 10
        "Tôi có bao nhiêu sổ tiết kiệm",
        "Xem danh sách tất cả sổ tiết kiệm của tôi",
        "Kiểm tra các khoản tiết kiệm hiện có",
        "Cho tôi biết tổng số tiền tiết kiệm",
        "Liệt kê các sổ tiết kiệm đang có",
        "Tôi đang gửi tiết kiệm bao nhiêu",
        "Xem thông tin tất cả sổ tiết kiệm",
        "Các khoản tiết kiệm của tôi",
        "Tổng tiết kiệm hiện tại",
        "Danh sách STK của tôi",
        # Expanded
        "Tiết kiệm của tôi",
        "Xem STK",
        "Còn bao nhiêu tiền tiết kiệm",
        "Sổ tiết kiệm của mình",
        "Check tiết kiệm",
        "Tôi gửi tiết kiệm bao nhiêu rồi",
        "Savings của tôi",
        "Xem saving account",
        "Tổng tiền gửi tiết kiệm",
        "Các sổ TK của tôi",
        "Lãi suất tiết kiệm của tôi",
        "Sổ tiết kiệm đáo hạn khi nào",
        "Tiết kiệm kỳ hạn bao lâu",
        "Tôi có mấy sổ tiết kiệm",
        "List sổ tiết kiệm",
        "All savings của tôi",
        "Xem tất cả STK",
        "Tiền gửi của tôi",
        "Các khoản gửi tiết kiệm",
        "Sổ tiết kiệm còn hạn không",
    ],

    "getTransactionHistory": [
        # Original 10
        "Xem lịch sử giao dịch của tôi",
        "Cho tôi biết các giao dịch gần đây",
        "Kiểm tra lịch sử chuyển khoản",
        "Liệt kê các giao dịch trong tuần này",
        "Tôi đã giao dịch những gì",
        "Xem sao kê tài khoản",
        "Lịch sử chuyển tiền của tôi",
        "Các giao dịch tháng này",
        "Kiểm tra các khoản đã chi tiêu",
        "Xem history giao dịch",
        # Expanded
        "Giao dịch gần đây",
        "Xem GD",
        "Lịch sử GD của tôi",
        "Đã chuyển tiền cho ai",
        "Check lịch sử",
        "Tôi đã chuyển khoản cho ai",
        "Transaction history",
        "Các giao dịch đã thực hiện",
        "Sao kê giao dịch",
        "Lịch sử CK của tôi",
        "Tôi nhận tiền từ đâu",
        "Ai chuyển tiền cho tôi",
        "Giao dịch hôm nay",
        "GD tuần này",
        "Các khoản chi tiêu",
        "Xem các lần chuyển khoản",
        "History chuyển tiền",
        "Đã chi tiêu bao nhiêu",
        "Tiền vào tiền ra",
        "Biến động số dư",
    ],

    "getUserProfile": [
        # Original 10
        "Xem thông tin cá nhân của tôi",
        "Cho tôi biết profile của tôi",
        "Kiểm tra hồ sơ người dùng",
        "Thông tin tài khoản cá nhân",
        "Xem tên và địa chỉ của tôi",
        "Hồ sơ của tôi như thế nào",
        "Thông tin đăng ký của tôi",
        "Profile người dùng",
        "Xem info cá nhân",
        "Kiểm tra thông tin cá nhân",
        # Expanded
        "Thông tin của tôi",
        "Profile của mình",
        "Hồ sơ cá nhân",
        "Xem profile",
        "Info user",
        "Tên đăng ký của tôi",
        "Số điện thoại đăng ký",
        "Email của tôi là gì",
        "Địa chỉ của tôi",
        "CMND/CCCD đăng ký",
        "Ngày sinh của tôi",
        "Thông tin KYC",
        "User info",
        "Personal information",
        "My profile",
        "Xem tài khoản cá nhân",
        "Thông tin người dùng",
        "Account profile",
        "Tên tôi là gì",
        "Chi tiết hồ sơ",
    ],

    "getTransactionList": [
        # Original 10
        "Liệt kê danh sách giao dịch",
        "Xem tất cả các giao dịch",
        "Cho tôi danh sách các lần chuyển khoản",
        "Danh sách giao dịch của tôi",
        "Xem list các giao dịch",
        "Tất cả giao dịch đã thực hiện",
        "Danh sách CK của tôi",
        "List transaction",
        "Các giao dịch của tôi",
        "Xem danh sách GD",
        # Expanded
        "Danh sách GD",
        "List giao dịch",
        "Tất cả GD",
        "Xem list CK",
        "Danh sách chuyển tiền",
        "All transactions",
        "Full list giao dịch",
        "Toàn bộ giao dịch",
        "DS chuyển khoản",
        "List CK đã thực hiện",
        "Xem tất cả chuyển khoản",
        "Danh sách các lần chuyển",
        "Giao dịch từ trước đến giờ",
        "Tổng hợp giao dịch",
        "Thống kê giao dịch",
        "Báo cáo giao dịch",
        "Transaction list",
        "Xem toàn bộ GD",
        "Full transaction history",
        "Complete list GD",
    ],
}


# =============================================================================
# ENHANCED VARIATION GENERATORS
# =============================================================================

def apply_all_synonyms(text: str) -> Set[str]:
    """Thay thế tất cả từ đồng nghĩa có thể"""
    results = {text}

    for word, synonyms in SYNONYMS_MAP.items():
        if word.lower() in text.lower():
            for syn in synonyms:
                new_text = re.sub(re.escape(word), syn, text, flags=re.IGNORECASE)
                new_text = re.sub(r'\s+', ' ', new_text).strip()
                if new_text and new_text != text:
                    results.add(new_text)

    return results


def apply_all_pronouns(text: str) -> Set[str]:
    """Thay đổi tất cả đại từ có thể"""
    results = {text}

    for word, replacements in PRONOUNS_MAP.items():
        if word.lower() in text.lower():
            for rep in replacements:
                new_text = re.sub(re.escape(word), rep, text, flags=re.IGNORECASE)
                new_text = re.sub(r'\s+', ' ', new_text).strip()
                if new_text and new_text != text and len(new_text) > 3:
                    results.add(new_text)

    return results


def apply_all_verbs(text: str) -> Set[str]:
    """Thay đổi tất cả động từ có thể"""
    results = {text}

    for word, replacements in VERBS_MAP.items():
        if word.lower() in text.lower():
            for rep in replacements:
                new_text = re.sub(re.escape(word), rep, text, flags=re.IGNORECASE)
                new_text = re.sub(r'\s+', ' ', new_text).strip()
                if new_text and new_text != text and len(new_text) > 3:
                    results.add(new_text)

    return results


def apply_prefixes(text: str) -> Set[str]:
    """Thêm tất cả prefix"""
    results = set()

    # Remove existing common prefixes
    clean_text = text
    remove_prefixes = ["Cho tôi ", "Tôi muốn ", "Tôi cần ", "Giúp tôi ", "Vui lòng ",
                       "Làm ơn ", "Xin ", "Cho mình ", "Mình muốn ", "Em muốn "]
    for prefix in remove_prefixes:
        if clean_text.lower().startswith(prefix.lower()):
            clean_text = clean_text[len(prefix):]
            break

    for prefix in PREFIXES:
        new_text = prefix + clean_text
        if new_text:
            new_text = new_text[0].upper() + new_text[1:] if len(new_text) > 1 else new_text.upper()
            results.add(new_text.strip())

    return results


def apply_suffixes(text: str) -> Set[str]:
    """Thêm tất cả suffix"""
    results = set()
    clean_text = text.rstrip("?!.,;")

    for suffix in SUFFIXES:
        results.add(clean_text + suffix)

    return results


def apply_typos(text: str, num_typos: int = 5) -> Set[str]:
    """Tạo các biến thể lỗi chính tả"""
    results = {text}

    for word, typos in TYPOS_MAP.items():
        if word.lower() in text.lower():
            sample_typos = random.sample(typos, min(num_typos, len(typos)))
            for typo in sample_typos:
                new_text = re.sub(re.escape(word), typo, text, flags=re.IGNORECASE)
                if new_text != text:
                    results.add(new_text)

    return results


def apply_abbreviations(text: str) -> Set[str]:
    """Thay thế bằng viết tắt teen/chat"""
    results = {text}

    for word, abbrs in ABBREVIATIONS.items():
        if word.lower() in text.lower():
            for abbr in abbrs:
                new_text = re.sub(re.escape(word), abbr, text, flags=re.IGNORECASE)
                new_text = re.sub(r'\s+', ' ', new_text).strip()
                if new_text and new_text != text:
                    results.add(new_text)

    return results


def apply_code_mix(text: str) -> Set[str]:
    """Thay thế bằng từ tiếng Anh (code-mixing)"""
    results = {text}

    for word, eng_words in CODE_MIX.items():
        if word.lower() in text.lower():
            for eng in eng_words:
                new_text = re.sub(re.escape(word), eng, text, flags=re.IGNORECASE)
                new_text = re.sub(r'\s+', ' ', new_text).strip()
                if new_text and new_text != text:
                    results.add(new_text)

    return results


def apply_case_variations(text: str) -> Set[str]:
    """Thay đổi viết hoa/thường"""
    return {
        text,
        text.lower(),
        text.upper(),
        text.capitalize(),
        text.title(),
    }


def apply_regional(text: str) -> Set[str]:
    """Thay đổi theo vùng miền"""
    results = {text}

    for word, regionals in REGIONAL.items():
        if word.lower() in text.lower():
            for reg in regionals:
                new_text = re.sub(re.escape(word), reg, text, flags=re.IGNORECASE)
                new_text = re.sub(r'\s+', ' ', new_text).strip()
                if new_text and new_text != text:
                    results.add(new_text)

    return results


def generate_all_variations(base_question: str) -> Set[str]:
    """Generate tất cả variations có thể cho một câu hỏi gốc"""
    all_variations = {base_question}

    # ========== Layer 1: Single transformations ==========
    all_variations.update(apply_all_synonyms(base_question))
    all_variations.update(apply_all_pronouns(base_question))
    all_variations.update(apply_all_verbs(base_question))
    all_variations.update(apply_prefixes(base_question))
    all_variations.update(apply_suffixes(base_question))
    all_variations.update(apply_abbreviations(base_question))
    all_variations.update(apply_code_mix(base_question))
    all_variations.update(apply_regional(base_question))
    all_variations.update(apply_case_variations(base_question))

    # ========== Layer 2: Double combinations ==========
    layer1_sample = random.sample(list(all_variations), min(100, len(all_variations)))

    for var in layer1_sample:
        # Synonym + Suffix
        for syn_var in list(apply_all_synonyms(var))[:10]:
            all_variations.update(list(apply_suffixes(syn_var))[:10])

        # Prefix + Pronoun
        for pre_var in list(apply_prefixes(var))[:10]:
            all_variations.update(list(apply_all_pronouns(pre_var))[:10])

        # Verb + Suffix
        for verb_var in list(apply_all_verbs(var))[:10]:
            all_variations.update(list(apply_suffixes(verb_var))[:10])

        # Abbreviation + Suffix
        for abbr_var in list(apply_abbreviations(var))[:10]:
            all_variations.update(list(apply_suffixes(abbr_var))[:10])

        # Code-mix + Suffix
        for code_var in list(apply_code_mix(var))[:10]:
            all_variations.update(list(apply_suffixes(code_var))[:10])

    # ========== Layer 3: Triple combinations (sampled) ==========
    layer2_sample = random.sample(list(all_variations), min(200, len(all_variations)))

    for var in layer2_sample:
        # Prefix + Synonym + Suffix
        for pre_var in list(apply_prefixes(var))[:5]:
            for syn_var in list(apply_all_synonyms(pre_var))[:5]:
                all_variations.update(list(apply_suffixes(syn_var))[:5])

        # Pronoun + Verb + Suffix
        for pro_var in list(apply_all_pronouns(var))[:5]:
            for verb_var in list(apply_all_verbs(pro_var))[:5]:
                all_variations.update(list(apply_suffixes(verb_var))[:5])

    # ========== Layer 4: Add typos to some variations ==========
    typo_sample = random.sample(list(all_variations), min(100, len(all_variations)))
    for var in typo_sample:
        all_variations.update(apply_typos(var, num_typos=3))

    # ========== Clean and filter ==========
    cleaned = set()
    for var in all_variations:
        var = re.sub(r'\s+', ' ', var).strip()
        # Filter out too short or invalid
        if var and len(var) >= 3:
            # Remove double prefixes artifacts
            if not re.match(r'^(Cho|Tôi|Mình|Em|Giúp|Vui|Làm|Xin).*(Cho|Tôi muốn|Mình muốn|Em muốn)', var):
                cleaned.add(var)

    return cleaned


def generate_api_testdata(api_name: str, output_path: str, target_count: int = 5000):
    """Generate test data CSV for an API"""
    questions = API_QUESTIONS.get(api_name, [])
    if not questions:
        print(f"No questions defined for {api_name}")
        return 0

    all_variations = []
    seen = set()

    print(f"  Generating variations for {api_name}...")

    for i, base_q in enumerate(questions):
        variations = generate_all_variations(base_q)

        for var in variations:
            var_lower = var.lower()
            if var_lower not in seen:
                seen.add(var_lower)
                all_variations.append({
                    "question": var,
                    "base_question": base_q,
                    "api": api_name,
                })

        if (i + 1) % 10 == 0:
            print(f"    Processed {i+1}/{len(questions)} base questions, {len(all_variations)} variations so far")

    # Shuffle
    random.shuffle(all_variations)

    # If we have more than target, sample; otherwise keep all
    if len(all_variations) > target_count:
        all_variations = random.sample(all_variations, target_count)

    # Write CSV
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["question", "base_question", "api"])
        writer.writeheader()
        writer.writerows(all_variations)

    print(f"  -> Generated {len(all_variations)} questions for {api_name}")
    return len(all_variations)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import os

    print("=" * 60)
    print("TEST DATA GENERATOR V2 - EXPANDED")
    print("=" * 60)

    output_dir = os.path.dirname(os.path.abspath(__file__))

    apis = [
        ("getAccountDetail", "accountdetails.csv", 5000),
        ("getAllSavings", "allsavings.csv", 5000),
        ("getTransactionHistory", "transactionhistory.csv", 5000),
        ("getUserProfile", "userprofile.csv", 5000),
        ("getTransactionList", "transactionlist.csv", 5000),
    ]

    total = 0
    for api_name, filename, target in apis:
        print(f"\n[{api_name}]")
        output_path = os.path.join(output_dir, filename)
        count = generate_api_testdata(api_name, output_path, target_count=target)
        total += count

    print(f"\n{'=' * 60}")
    print(f"TOTAL: {total:,} test questions generated")
    print(f"{'=' * 60}")
