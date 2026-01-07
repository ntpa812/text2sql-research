"""
Generate CLEAN test data - V3
Focus on distinctive keywords for each API to avoid ambiguity
"""
import csv
import random
import re
from typing import List, Set

# =============================================================================
# DISTINCTIVE KEYWORDS FOR EACH API
# These words should ONLY appear in queries for their respective API
# =============================================================================

API_DISTINCTIVE_KEYWORDS = {
    "getAccountDetail": [
        "số dư", "balance", "tiền trong", "còn bao nhiêu tiền",
        "chi nhánh mở", "hạn mức thấu chi", "loại tài khoản", "thuộc loại",
        "trạng thái tài khoản", "đang hoạt động", "số tài khoản",
        "loại tiền", "sản phẩm", "tên sản phẩm",
    ],
    "getAllSavings": [
        "tiết kiệm", "sổ tiết kiệm", "stk", "saving", "gửi tiết kiệm",
        "đáo hạn", "kỳ hạn", "lãi suất", "tiền gửi",
    ],
    "getTransactionHistory": [
        "lịch sử giao dịch", "giao dịch gần đây", "sao kê",
        "đã giao dịch", "chuyển khoản", "chi tiêu",
        "tiền vào", "tiền ra", "biến động",
    ],
    "getUserProfile": [
        "cá nhân", "hồ sơ", "profile", "email", "số điện thoại",
        "họ tên", "địa chỉ", "cmnd", "cccd", "ngày sinh", "kyc",
        "thông tin đăng ký", "user", "người dùng",
    ],
    "getTransactionList": [
        "danh sách giao dịch", "list giao dịch", "tất cả giao dịch",
        "liệt kê giao dịch", "các lần chuyển", "toàn bộ giao dịch",
    ],
}

# Words that are TOO AMBIGUOUS - avoid using alone
AMBIGUOUS_WORDS = [
    "thông tin", "info", "xem", "kiểm tra", "check", "coi", "tra cứu",
    "tài khoản", "tk", "account", "acc",  # These need context
]

# =============================================================================
# CLEAN VARIATION RULES - No Gen Z slang, minimal typos
# =============================================================================

PRONOUNS = {
    "của tôi": ["của mình", "của em", "của tui", ""],
    "tôi": ["mình", "em", "tui", ""],
}

VERBS = {
    "xem": ["kiểm tra", "cho biết", "hiển thị"],
    "cho biết": ["cho xem", "xem"],
    "kiểm tra": ["xem", "tra cứu"],
}

# Only use SAFE synonyms that don't cause confusion
SYNONYMS_SAFE = {
    "số dư": ["balance", "tiền còn", "số tiền"],
    "tiết kiệm": ["saving", "gửi tiết kiệm"],
    "giao dịch": ["transaction"],
    "ngân hàng": ["NH", "bank"],
    "hiện tại": ["bây giờ", "lúc này", ""],
    "bao nhiêu": ["là gì", "được bao nhiêu"],
}

# CLEAN prefixes - no Gen Z slang
PREFIXES_CLEAN = [
    "", "Cho tôi ", "Tôi muốn ", "Tôi cần ",
    "Giúp tôi ", "Vui lòng ", "Làm ơn ",
    "Cho mình ", "Mình muốn ",
    "Có thể ", "Được không nếu ",
]

# CLEAN suffixes - no Gen Z slang
SUFFIXES_CLEAN = [
    "", "?", " được không", " được không?",
    " nhé", " nha", " với", " ạ",
    " giùm", " giúp với",
]


# =============================================================================
# CLEAN BASE QUESTIONS - Each MUST contain distinctive keywords
# =============================================================================

API_QUESTIONS_CLEAN = {
    "getAccountDetail": [
        # Focus on số dư, balance
        "Số dư tài khoản của tôi là bao nhiêu",
        "Xem số dư tài khoản",
        "Kiểm tra số dư",
        "Balance tài khoản của tôi",
        "Tiền trong tài khoản còn bao nhiêu",
        "Còn bao nhiêu tiền trong tài khoản",
        # Focus on chi nhánh, trạng thái
        "Chi nhánh mở tài khoản của tôi",
        "Tài khoản mở ở chi nhánh nào",
        "Trạng thái tài khoản của tôi",
        "Tài khoản còn hoạt động không",
        "Tài khoản đang hoạt động không",
        # Focus on loại tài khoản, hạn mức
        "Tài khoản của tôi thuộc loại nào",
        "Loại tài khoản của tôi là gì",
        "Hạn mức thấu chi của tài khoản",
        "Xem hạn mức thấu chi",
        # Focus on số tài khoản, sản phẩm
        "Số tài khoản của tôi là gì",
        "Cho biết số tài khoản",
        "Tên sản phẩm tài khoản",
        "Loại tiền của tài khoản",
        # Chi tiết với distinctive words
        "Xem chi tiết số dư tài khoản",
        "Kiểm tra chi tiết số dư",
    ],

    "getAllSavings": [
        "Xem danh sách sổ tiết kiệm",
        "Tôi có bao nhiêu sổ tiết kiệm",
        "Các sổ tiết kiệm của tôi",
        "Tổng tiền tiết kiệm",
        "Kiểm tra tiết kiệm của tôi",
        "Lãi suất tiết kiệm hiện tại",
        "Sổ tiết kiệm sắp đáo hạn",
        "Kỳ hạn tiết kiệm của tôi",
        "Tiền gửi tiết kiệm",
        "Xem saving của tôi",
    ],

    "getTransactionHistory": [
        "Xem lịch sử giao dịch",
        "Giao dịch gần đây của tôi",
        "Kiểm tra sao kê tài khoản",
        "Các giao dịch đã thực hiện",
        "Lịch sử chuyển khoản",
        "Đã chi tiêu bao nhiêu",
        "Tiền vào tiền ra tháng này",
        "Biến động số dư gần đây",
    ],

    "getUserProfile": [
        "Xem thông tin cá nhân của tôi",
        "Hồ sơ người dùng của tôi",
        "Profile của tôi",
        "Email đăng ký của tôi",
        "Số điện thoại đăng ký",
        "Họ tên đăng ký của tôi",
        "Địa chỉ của tôi",
        "Thông tin KYC của tôi",
        "Xem thông tin user",
    ],

    "getTransactionList": [
        "Danh sách tất cả giao dịch",
        "Liệt kê các giao dịch",
        "List toàn bộ giao dịch",
        "Xem danh sách giao dịch đã thực hiện",
        "Tất cả các lần chuyển khoản",
    ],
}


# =============================================================================
# CLEAN VARIATION GENERATORS
# =============================================================================

def apply_safe_synonym(text: str) -> Set[str]:
    """Only apply synonyms that don't cause confusion"""
    results = {text}
    for word, synonyms in SYNONYMS_SAFE.items():
        if word.lower() in text.lower():
            for syn in synonyms:
                new_text = re.sub(re.escape(word), syn, text, flags=re.IGNORECASE)
                new_text = re.sub(r'\s+', ' ', new_text).strip()
                if new_text and new_text != text:
                    results.add(new_text)
    return results


def apply_pronoun(text: str) -> Set[str]:
    results = {text}
    for word, replacements in PRONOUNS.items():
        if word.lower() in text.lower():
            for rep in replacements:
                new_text = re.sub(re.escape(word), rep, text, flags=re.IGNORECASE)
                new_text = re.sub(r'\s+', ' ', new_text).strip()
                if new_text and new_text != text and len(new_text) > 5:
                    results.add(new_text)
    return results


def apply_verb(text: str) -> Set[str]:
    results = {text}
    for word, replacements in VERBS.items():
        if word.lower() in text.lower():
            for rep in replacements:
                new_text = re.sub(re.escape(word), rep, text, flags=re.IGNORECASE)
                new_text = re.sub(r'\s+', ' ', new_text).strip()
                if new_text and new_text != text:
                    results.add(new_text)
    return results


def apply_prefix(text: str) -> Set[str]:
    results = set()
    clean_text = text
    for prefix in ["Cho tôi ", "Tôi muốn ", "Tôi cần ", "Giúp tôi ", "Vui lòng "]:
        if clean_text.lower().startswith(prefix.lower()):
            clean_text = clean_text[len(prefix):]
            break

    for prefix in PREFIXES_CLEAN:
        new_text = prefix + clean_text
        if new_text:
            new_text = new_text[0].upper() + new_text[1:] if len(new_text) > 1 else new_text.upper()
            results.add(new_text.strip())
    return results


def apply_suffix(text: str) -> Set[str]:
    results = set()
    clean_text = text.rstrip("?!.,")
    for suffix in SUFFIXES_CLEAN:
        results.add(clean_text + suffix)
    return results


def has_distinctive_keyword(text: str, api: str) -> bool:
    """Check if text contains at least one distinctive keyword for the API"""
    text_lower = text.lower()
    keywords = API_DISTINCTIVE_KEYWORDS.get(api, [])
    return any(kw.lower() in text_lower for kw in keywords)


def is_ambiguous(text: str, target_api: str) -> bool:
    """Check if text could match another API"""
    text_lower = text.lower()

    # Check if it has distinctive keywords for OTHER APIs
    for api, keywords in API_DISTINCTIVE_KEYWORDS.items():
        if api == target_api:
            continue
        if any(kw.lower() in text_lower for kw in keywords):
            return True

    return False


def generate_clean_variations(base_question: str, api: str) -> Set[str]:
    """Generate clean variations that maintain distinctive keywords"""
    all_variations = {base_question}

    # Layer 1: Single transformations
    all_variations.update(apply_safe_synonym(base_question))
    all_variations.update(apply_pronoun(base_question))
    all_variations.update(apply_verb(base_question))
    all_variations.update(apply_prefix(base_question))
    all_variations.update(apply_suffix(base_question))

    # Layer 2: Double combinations (limited)
    layer1_sample = list(all_variations)[:30]
    for var in layer1_sample:
        for syn_var in list(apply_safe_synonym(var))[:5]:
            all_variations.update(list(apply_suffix(syn_var))[:5])

        for pre_var in list(apply_prefix(var))[:5]:
            all_variations.update(list(apply_pronoun(pre_var))[:5])

    # FILTER: Only keep variations that have distinctive keywords
    # and are not ambiguous
    filtered = set()
    for var in all_variations:
        var = re.sub(r'\s+', ' ', var).strip()
        if not var or len(var) < 10:
            continue

        # Must have distinctive keyword
        if not has_distinctive_keyword(var, api):
            continue

        # Should not be ambiguous (match other APIs)
        if is_ambiguous(var, api):
            continue

        filtered.add(var)

    return filtered


def generate_api_testdata(api_name: str, output_path: str, target_count: int = 1000):
    """Generate clean test data CSV for an API"""
    questions = API_QUESTIONS_CLEAN.get(api_name, [])
    if not questions:
        print(f"No questions defined for {api_name}")
        return 0

    all_variations = []
    seen = set()

    print(f"  Generating clean variations for {api_name}...")

    for base_q in questions:
        variations = generate_clean_variations(base_q, api_name)
        for var in variations:
            var_lower = var.lower()
            if var_lower not in seen:
                seen.add(var_lower)
                all_variations.append({
                    "question": var,
                    "base_question": base_q,
                    "api": api_name,
                })

    print(f"    Generated {len(all_variations)} unique variations")

    # Shuffle and limit
    random.shuffle(all_variations)
    if len(all_variations) > target_count:
        all_variations = all_variations[:target_count]

    # Write CSV
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=["question", "base_question", "api"])
        writer.writeheader()
        writer.writerows(all_variations)

    print(f"  -> Saved {len(all_variations)} questions for {api_name}")
    return len(all_variations)


# =============================================================================
# MAIN
# =============================================================================

if __name__ == "__main__":
    import os

    print("=" * 60)
    print("TEST DATA GENERATOR V3 - CLEAN (No ambiguity)")
    print("=" * 60)

    output_dir = os.path.dirname(os.path.abspath(__file__))

    apis = [
        ("getAccountDetail", "accountdetails_clean.csv", 1000),
        ("getAllSavings", "allsavings_clean.csv", 500),
        ("getTransactionHistory", "transactionhistory_clean.csv", 500),
        ("getUserProfile", "userprofile_clean.csv", 500),
        ("getTransactionList", "transactionlist_clean.csv", 300),
    ]

    total = 0
    for api_name, filename, target in apis:
        print(f"\n[{api_name}]")
        output_path = os.path.join(output_dir, filename)
        count = generate_api_testdata(api_name, output_path, target_count=target)
        total += count

    print(f"\n{'=' * 60}")
    print(f"TOTAL: {total:,} CLEAN test questions generated")
    print(f"{'=' * 60}")
