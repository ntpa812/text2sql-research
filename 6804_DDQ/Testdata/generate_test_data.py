"""
Generate test data variations for Vietnamese banking questions
Applies 50+ variation methods to create thousands of test questions
"""
import csv
import random
import re
from typing import List, Dict, Tuple
from itertools import product

# =============================================================================
# VARIATION RULES
# =============================================================================

# Nhóm 1: Đại từ nhân xưng
PRONOUNS = {
    "của tôi": ["của mình", "của em", "của tui", "của t", "tôi", "mình", ""],
    "tôi": ["mình", "em", "tui", "t", ""],
    "cho tôi": ["cho mình", "cho em", "cho tui", "giùm tôi", "giúp tôi"],
}

# Nhóm 2: Động từ
VERBS = {
    "xem": ["kiểm tra", "check", "coi", "tra cứu", "xem xét", "show", "hiển thị"],
    "cho biết": ["cho xem", "cho hay", "nói cho biết", "thông báo"],
    "muốn": ["cần", "mong", "thích", ""],
    "kiểm tra": ["check", "xem", "tra", "dò"],
}

# Nhóm 3: Từ vựng đồng nghĩa
SYNONYMS = {
    "tài khoản": ["TK", "account", "acc", "tk", "tài khoản ngân hàng", "tài khoản NH"],
    "số dư": ["balance", "tiền", "số tiền", "dư", "số dư hiện có"],
    "chi tiết": ["thông tin", "info", "details", ""],
    "ngân hàng": ["NH", "bank", "ngân hàng Proton", ""],
    "hiện tại": ["bây giờ", "lúc này", "hiện giờ", "hiện", ""],
    "bao nhiêu": ["bn", "bnh", "là gì", "sao", "thế nào"],
    "còn": ["đang có", "có", "đang còn", "hiện còn"],
    "sổ tiết kiệm": ["STK", "tiết kiệm", "sổ TK", "saving", "sổ", "tài khoản tiết kiệm"],
    "giao dịch": ["GD", "transaction", "gd", "lịch sử GD"],
    "lịch sử": ["history", "LS", "ls", "quá khứ"],
    "thông tin cá nhân": ["profile", "hồ sơ", "thông tin", "info cá nhân"],
    "chuyển tiền": ["chuyển khoản", "CK", "transfer", "chuyển"],
}

# Nhóm 4: Cấu trúc câu - Prefix
PREFIXES = [
    "", "Cho tôi ", "Tôi muốn ", "Tôi cần ", "Giúp tôi ",
    "Làm ơn ", "Vui lòng ", "Có thể ", "Được không nếu ",
    "Mình muốn ", "Em muốn ", "Cho mình ", "Giùm tôi ",
    "Nhanh ", "Ê ", "Ơi ", "Hey ", "Cho xem ", "Show ",
]

# Nhóm 5: Suffix
SUFFIXES = [
    "", " được không", " nhé", " nha", " với", " đi", " cái",
    " ạ", " luôn", " giùm", " hen", " nghen", " real quick",
    " nhanh", " gấp", " liền", "?", " vậy", " xíu",
]

# Nhóm 6: Lỗi chính tả phổ biến
TYPOS = {
    "tài khoản": ["tai khoan", "tai khoản", "tài khon", "tài khoăn"],
    "số dư": ["so du", "sô dư", "số du", "so dư"],
    "kiểm tra": ["kiem tra", "kiêm tra", "kiểm tra"],
    "chi tiết": ["chi tiet", "chy tiết", "chi tiêt"],
    "giao dịch": ["giao dich", "giao dịhc", "gd"],
    "tiết kiệm": ["tiet kiem", "tiêt kiệm", "tiet kiệm"],
    "lịch sử": ["lich su", "lịch sừ", "lich sử"],
    "chuyển khoản": ["chuyen khoan", "chuyên khoản", "chuyển khon"],
}


# =============================================================================
# BASE QUESTIONS FOR EACH API
# =============================================================================

API_QUESTIONS = {
    "getAccountDetail": [
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
        # Thêm câu bổ sung
        "Tài khoản còn tiền không",
        "Số dư khả dụng là bao nhiêu",
        "Kiểm tra tiền trong tài khoản",
        "Xem số dư",
        "TK của tôi",
    ],

    "getAllSavings": [
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
        # Thêm câu bổ sung
        "Tiết kiệm của tôi",
        "Xem STK",
        "Còn bao nhiêu tiền tiết kiệm",
        "Sổ tiết kiệm của mình",
        "Check tiết kiệm",
    ],

    "getTransactionHistory": [
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
        # Thêm câu bổ sung
        "Giao dịch gần đây",
        "Xem GD",
        "Lịch sử GD của tôi",
        "Đã chuyển tiền cho ai",
        "Check lịch sử",
    ],

    "getUserProfile": [
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
        # Thêm câu bổ sung
        "Thông tin của tôi",
        "Profile của mình",
        "Hồ sơ cá nhân",
        "Xem profile",
        "Info user",
    ],

    "getTransactionList": [
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
        # Thêm câu bổ sung
        "Danh sách GD",
        "List giao dịch",
        "Tất cả GD",
        "Xem list CK",
        "Danh sách chuyển tiền",
    ],
}


# =============================================================================
# VARIATION GENERATORS
# =============================================================================

def apply_synonym(text: str) -> List[str]:
    """Thay thế từ đồng nghĩa"""
    results = [text]
    for word, synonyms in SYNONYMS.items():
        if word in text.lower():
            for syn in synonyms:
                new_text = re.sub(re.escape(word), syn, text, flags=re.IGNORECASE)
                if new_text != text:
                    results.append(new_text)
    return results

def apply_pronoun(text: str) -> List[str]:
    """Thay đổi đại từ nhân xưng"""
    results = [text]
    for word, replacements in PRONOUNS.items():
        if word in text.lower():
            for rep in replacements:
                new_text = re.sub(re.escape(word), rep, text, flags=re.IGNORECASE)
                new_text = re.sub(r'\s+', ' ', new_text).strip()
                if new_text and new_text != text:
                    results.append(new_text)
    return results

def apply_verb(text: str) -> List[str]:
    """Thay đổi động từ"""
    results = [text]
    for word, replacements in VERBS.items():
        if word in text.lower():
            for rep in replacements:
                new_text = re.sub(re.escape(word), rep, text, flags=re.IGNORECASE)
                new_text = re.sub(r'\s+', ' ', new_text).strip()
                if new_text and new_text != text:
                    results.append(new_text)
    return results

def apply_prefix(text: str) -> List[str]:
    """Thêm prefix"""
    results = []
    # Remove existing common prefixes first
    clean_text = text
    for prefix in ["Cho tôi ", "Tôi muốn ", "Tôi cần ", "Giúp tôi ", "Vui lòng ", "Làm ơn "]:
        if clean_text.lower().startswith(prefix.lower()):
            clean_text = clean_text[len(prefix):]
            break

    for prefix in PREFIXES:
        new_text = prefix + clean_text
        new_text = new_text[0].upper() + new_text[1:] if new_text else ""
        results.append(new_text.strip())
    return results

def apply_suffix(text: str) -> List[str]:
    """Thêm suffix"""
    results = []
    # Remove existing punctuation
    clean_text = text.rstrip("?!.,")
    for suffix in SUFFIXES:
        results.append(clean_text + suffix)
    return results

def apply_typo(text: str) -> List[str]:
    """Tạo lỗi chính tả"""
    results = [text]
    for word, typos in TYPOS.items():
        if word in text.lower():
            for typo in random.sample(typos, min(2, len(typos))):
                new_text = re.sub(re.escape(word), typo, text, flags=re.IGNORECASE)
                if new_text != text:
                    results.append(new_text)
    return results

def apply_case_variation(text: str) -> List[str]:
    """Thay đổi viết hoa/thường"""
    return [
        text,
        text.lower(),
        text.upper(),
        text.capitalize(),
    ]


def generate_variations(base_question: str, max_per_question: int = 100) -> List[str]:
    """Generate all variations for a base question"""
    all_variations = set()
    all_variations.add(base_question)

    # Layer 1: Apply each variation method independently
    synonyms = apply_synonym(base_question)
    pronouns = apply_pronoun(base_question)
    verbs = apply_verb(base_question)
    prefixes = apply_prefix(base_question)
    suffixes = apply_suffix(base_question)
    typos = apply_typo(base_question)
    cases = apply_case_variation(base_question)

    # Add all single-method variations
    for var_list in [synonyms, pronouns, verbs, prefixes, suffixes, typos, cases]:
        all_variations.update(var_list)

    # Layer 2: Combine methods (sample to avoid explosion)
    base_variations = list(all_variations)[:30]

    for var in base_variations:
        # Apply synonym + suffix
        for syn_var in apply_synonym(var)[:5]:
            for suf_var in apply_suffix(syn_var)[:5]:
                all_variations.add(suf_var)

        # Apply prefix + pronoun
        for pre_var in apply_prefix(var)[:5]:
            for pro_var in apply_pronoun(pre_var)[:5]:
                all_variations.add(pro_var)

        # Apply verb + suffix
        for verb_var in apply_verb(var)[:5]:
            for suf_var in apply_suffix(verb_var)[:5]:
                all_variations.add(suf_var)

    # Layer 3: Add some typos to existing variations
    sample_vars = random.sample(list(all_variations), min(20, len(all_variations)))
    for var in sample_vars:
        all_variations.update(apply_typo(var)[:3])

    # Clean and filter
    cleaned = set()
    for var in all_variations:
        var = re.sub(r'\s+', ' ', var).strip()
        if var and len(var) > 2:
            cleaned.add(var)

    # Limit per question
    result = list(cleaned)
    if len(result) > max_per_question:
        result = random.sample(result, max_per_question)

    return result


def generate_api_testdata(api_name: str, output_path: str, target_count: int = 1000):
    """Generate test data CSV for an API"""
    questions = API_QUESTIONS.get(api_name, [])
    if not questions:
        print(f"No questions defined for {api_name}")
        return

    all_variations = []
    variations_per_question = target_count // len(questions) + 20

    for base_q in questions:
        variations = generate_variations(base_q, max_per_question=variations_per_question)
        for var in variations:
            all_variations.append({
                "question": var,
                "base_question": base_q,
                "api": api_name,
            })

    # Shuffle and limit
    random.shuffle(all_variations)
    all_variations = all_variations[:target_count]

    # Write CSV
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["question", "base_question", "api"])
        writer.writeheader()
        writer.writerows(all_variations)

    print(f"Generated {len(all_variations)} questions for {api_name} -> {output_path}")
    return len(all_variations)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import os

    # Output directory
    output_dir = os.path.dirname(os.path.abspath(__file__))

    # Generate for each API
    apis = [
        ("getAccountDetail", "accountdetails.csv"),
        ("getAllSavings", "allsavings.csv"),
        ("getTransactionHistory", "transactionhistory.csv"),
        ("getUserProfile", "userprofile.csv"),
        ("getTransactionList", "transactionlist.csv"),
    ]

    total = 0
    for api_name, filename in apis:
        output_path = os.path.join(output_dir, filename)
        count = generate_api_testdata(api_name, output_path, target_count=1000)
        total += count

    print(f"\n{'='*50}")
    print(f"TOTAL: {total} test questions generated")
    print(f"{'='*50}")
