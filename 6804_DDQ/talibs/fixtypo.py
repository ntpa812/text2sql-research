# coding: utf-8
"""
Module fixtypo: Thay thế các từ viết sai/typo thành từ đúng tiếng Việt.
Sử dụng dictionary từ file ABBR_configs.yml

Tối ưu tốc độ: Dùng split + dict lookup thay vì regex
"""

import re
import unicodedata
from typing import List, Dict, Optional

from tatools01.ParamsBase import TactParameters

AppName = 'ABBR_configs'


class Params_01(TactParameters):
    """Load config từ file YAML"""
    def __init__(self):
        super().__init__(ModuleName="ReplacingWords", params_dir='./')
        self.add_new_words = {}
        self.words = {}
        self.FILLER_WORDS = {}
        self.load_then_save_to_yaml(file_path=f"{AppName}.yml")
        
        if 'xâu sai' in self.add_new_words:
            del self.add_new_words['xâu sai']
        if len(self.add_new_words)>0:            
            # Merge từng từ mới vào đúng branch
            for key, value in self.add_new_words.items(): 
                t1 = key[0]  # Lấy ký tự đầu tiên làm branch key
                if t1 not in self.words:
                    self.words[t1] = {}
                self.words[t1][key] = value  # Thêm/update từ vào branch

            # Clear add_new_words sau khi đã merge
            self.add_new_words = {'xâu sai':'xâu đúng'}

            self.sort_words()
            self.save_to_yaml_only()
            # đọc dữ liệu cấu hình tại config: ABBR_configs.yml
        
    def sort_words(self):
        """Sort key cấp 1 và key cấp 2 của words_branch"""
        # Sort cấp 1
        sorted_lv1 = dict(sorted(self.words.items(), key=lambda x: x[0]))

        # Sort cấp 2
        for k in sorted_lv1.keys():
            sorted_lv1[k] = dict(sorted(sorted_lv1[k].items(), key=lambda x: x[0]))

        self.words = sorted_lv1


# INSTANCE CONFIG TOÀN CỤC
config = Params_01()

# Cache flatten cho lookup nhanh
_words_flat: Dict[str, str] = {}  # "tai" -> "tài" (từ đơn, flatten từ branches)
_phrases: Dict[str, str] = {}     # "tai khoan" -> "tài khoản" (cụm từ)
_phrase_starts: set = set()       # {"tai", "ngan"} - các từ có thể bắt đầu phrase
_max_phrase_len: int = 1          # Độ dài phrase tối đa (số token)


def _build_cache():
    """Build cache flatten từ config.words"""
    global _words_flat, _phrases, _phrase_starts, _max_phrase_len

    _words_flat = {}
    _phrases = {}
    _phrase_starts = set()
    _max_phrase_len = 1

    # Duyệt qua tất cả branches và flatten
    for branch in config.words.values():
        for key, value in branch.items():
            if ' ' in key:
                # Đây là phrase (nhiều token)
                _phrases[key] = value
                first_word = key.split()[0]
                _phrase_starts.add(first_word)
                phrase_len = len(key.split())
                if phrase_len > _max_phrase_len:
                    _max_phrase_len = phrase_len
            else:
                # Từ đơn -> flatten vào dict chính
                _words_flat[key] = value


# Build cache khi load module
_build_cache()


def lookup_word(token: str) -> str:
    """Lookup từ đơn - O(1) với dict flatten"""
    if not token:
        return token
    return _words_flat.get(token.lower(), token)

from time import time
def tafix_tokens(tokens: List[str]) -> List[str]:
    """
    Sửa từng token trong danh sách.
    Hỗ trợ cả từ đơn và cụm từ (phrase).

    Args:
        tokens: Danh sách các token

    Returns:
        Danh sách token đã sửa
    """
    if not tokens:
        return tokens
    t0 = time() # pyright: ignore[reportCallIssue]
    # Nếu không có phrases, dùng cách nhanh nhất
    if not _phrase_starts:
        return [lookup_word(t) for t in tokens]

    # Có phrases -> cần greedy matching
    result = []
    i = 0
    n = len(tokens)

    # Cache local để tránh global lookup
    phrase_starts = _phrase_starts
    phrases = _phrases
    max_len = _max_phrase_len

    while i < n:
        token = tokens[i]
        token_lower = token.lower()

        # Kiểm tra xem token này có thể bắt đầu phrase không
        if token_lower in phrase_starts:
            # Thử match phrase dài nhất trước (greedy)
            matched = False
            for length in range(min(max_len, n - i), 1, -1):
                # Tạo phrase candidate
                phrase = ' '.join(tokens[j].lower() for j in range(i, i + length))
                if phrase in phrases:
                    result.append(phrases[phrase])
                    i += length
                    matched = True
                    break

            if not matched:
                # Không match phrase -> lookup từ đơn
                result.append(lookup_word(token))
                i += 1
        else:
            # Không thể bắt đầu phrase -> lookup từ đơn
            result.append(lookup_word(token))
            i += 1
    # print('Time 1 query (s):', time()-t0)
    return result


def tafix_tokens_fast(tokens: List[str]) -> List[str]:
    """
    Phiên bản siêu nhanh - CHỈ lookup từ đơn, bỏ qua phrases.
    Dùng khi biết chắc không cần match cụm từ.

    Args:
        tokens: Danh sách các token

    Returns:
        Danh sách token đã sửa
    """
    # Local reference để tránh global lookup mỗi iteration
    words = _words_flat
    return [words.get(t.lower(), t) for t in tokens]


class TypoFixer:
    """
    Class chuyên thay thế các từ viết sai/typo thành từ đúng tiếng Việt.

    Tối ưu tốc độ bằng phương pháp split + dict lookup (O(n) thay vì O(n*m) của regex)

    Usage:
        fixer = TypoFixer()
        fixed_text = fixer.fix("toi muon xem so du tai khoan")
        # Output: "tôi muốn xem số dư tài khoản"
    """

    # Regex để split text nhưng giữ lại delimiter (dấu câu, khoảng trắng)
    _SPLIT_PATTERN = re.compile(r'(\s+|[^\w\s]+)', re.UNICODE) 

    def _normalize(self, text: str) -> str:
        """Chuẩn hóa Unicode NFC."""
        return unicodedata.normalize("NFC", text) 

    def fix(self, text: str) -> str:
        """
        Sửa các từ viết sai trong text.
        Hỗ trợ cả từ đơn và cụm từ (phrase).

        Phương pháp: Split text thành tokens, dùng greedy phrase matching, join lại.
        Độ phức tạp: O(n) với n là số ký tự trong text.

        Args:
            text: Chuỗi cần sửa

        Returns:
            Chuỗi đã được sửa các từ viết sai
        """

        text = self._normalize(text)

        # Split giữ lại delimiter
        parts = self._SPLIT_PATTERN.split(text)

        # Tách words và delimiters
        words = []
        delimiters = []
        word_indices = []  # vị trí của words trong parts

        for idx, part in enumerate(parts):
            if part and not self._SPLIT_PATTERN.match(part):
                words.append(part)
                word_indices.append(idx)
            else:
                delimiters.append((idx, part))

        # Fix words với phrase support
        fixed_words = tafix_tokens(words)

        # Rebuild result - xử lý trường hợp phrase gộp nhiều từ
        result = list(parts)  # copy

        # Nếu số từ sau fix ít hơn (do phrase gộp), cần xử lý đặc biệt
        if len(fixed_words) != len(words):
            # Phrase đã gộp một số từ -> rebuild từ đầu
            # Đơn giản: join words đã fix với space
            return ' '.join(fixed_words)

        # Số từ bằng nhau -> thay thế tại chỗ
        for i, word_idx in enumerate(word_indices):
            result[word_idx] = fixed_words[i]

        return ''.join(result)

    def fix_fast(self, text: str) -> str:
        """
        Phiên bản siêu nhanh - split thành tokens, lookup dict, join lại.
        Không giữ case gốc, output các từ cách nhau bởi 1 space.

        Args:
            text: Chuỗi cần sửa

        Returns:
            Chuỗi đã sửa
        """ 

        # Split thành tokens
        tokens = self._normalize(text).split()

        # Lookup trực tiếp trong dict - O(1) cho mỗi token
        result = [lookup_word(t) for t in tokens]

        return ' '.join(result)

    def fix_tokens(self, tokens: List[str]) -> List[str]:
        """
        Sửa từng token trong danh sách.
        Đây là phương pháp nhanh nhất vì không cần split.

        Args:
            tokens: Danh sách các token

        Returns:
            Danh sách token đã sửa
        """ 

        # Lookup trực tiếp - O(1) cho mỗi token
        return [lookup_word(t) for t in tokens]


# INSTANCE TOÀN CỤC
typo_fixer = TypoFixer()

def fix_typo(text: str) -> str:
    """Hàm tiện ích để sửa typo nhanh."""
    return typo_fixer.fix(text)


def fix_typo_fast(text: str) -> str:
    """Hàm tiện ích sửa typo siêu nhanh (không giữ format gốc)."""
    return typo_fixer.fix_fast(text)


def fix_typo_tokens(tokens: List[str]) -> List[str]:
    """Hàm tiện ích để sửa typo cho danh sách token."""
    return typo_fixer.fix_tokens(tokens)


if __name__ == "__main__":
    import sys
    import io
    import time
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    print("=" * 60)
    print("TEST TYPO FIXER - OPTIMIZED VERSION")
    print("=" * 60)

    # Test cases
    test_cases = [
        "t muon xem so du tai khoan",
        "giup toi kich hoat quyen xem",
        "xin ho tro bat tinh nang xem so du",
        "phien ban mo quyen truy cap",
        "lam on cho phep toi xem thong tin",
        "nho ho tro kich hoat tai khoan ca nhan",
    ]

    print("\n[1] Test fix() - Sửa cả câu:")
    print("-" * 50)
    fixer = TypoFixer() 
    print()

    for text in test_cases:
        fixed = fixer.fix(text)
        print(f"IN : {text}")
        print(f"OUT: {fixed}")
        print()

    # Test 2: Benchmark
    print("\n[2] BENCHMARK - So sánh tốc độ:")
    print("-" * 50)

    # Tạo text dài để test
    long_text = " ".join(test_cases * 1000)  # 6000 câu
    iterations = 100

    # Test fix()
    start = time.perf_counter()
    for _ in range(iterations):
        fixer.fix(long_text)
    fix_time = time.perf_counter() - start

    # Test fix_fast()
    start = time.perf_counter()
    for _ in range(iterations):
        fixer.fix_fast(long_text)
    fix_fast_time = time.perf_counter() - start

    # Test fix_tokens() - tokens đã split sẵn (có phrase support)
    tokens = long_text.split()
    start = time.perf_counter()
    for _ in range(iterations):
        tafix_tokens(tokens)
    fix_tokens_time = time.perf_counter() - start

    # Test tafix_tokens_fast() - không có phrase support
    start = time.perf_counter()
    for _ in range(iterations):
        tafix_tokens_fast(tokens)
    fix_tokens_fast_time = time.perf_counter() - start

    print(f"Text length: {len(long_text):,} chars, {len(tokens):,} tokens")
    print(f"Phrases: {len(_phrases)}, Max phrase len: {_max_phrase_len}")
    print(f"Iterations: {iterations}")
    print()
    print(f"fix()              : {fix_time*1000:.2f} ms total, {fix_time/iterations*1000:.3f} ms/call")
    print(f"fix_fast()         : {fix_fast_time*1000:.2f} ms total, {fix_fast_time/iterations*1000:.3f} ms/call")
    print(f"tafix_tokens()     : {fix_tokens_time*1000:.2f} ms total, {fix_tokens_time/iterations*1000:.3f} ms/call")
    print(f"tafix_tokens_fast(): {fix_tokens_fast_time*1000:.2f} ms total, {fix_tokens_fast_time/iterations*1000:.3f} ms/call")
    print()
    print(f"tafix_tokens_fast() nhanh hơn fix(): {fix_time/fix_tokens_fast_time:.1f}x")
    print(f"tafix_tokens_fast() nhanh hơn tafix_tokens(): {fix_tokens_time/fix_tokens_fast_time:.1f}x")

    # Test 3: Các method khác
    print("\n[3] Test các method khác:")
    print("-" * 50) 

    print("\n" + "=" * 60)
    print("DONE!")
    print("=" * 60)






        # # Tạo branch
        # self.words_branch = {}
        # for key, value in self.words.items():
        #     t1 = key[0]
        #     if t1 not in self.words_branch:
        #         self.words_branch[t1] = {key: value}
        #     else:
        #         self.words_branch[t1][key] = value
        # # 👉 Sort toàn bộ các key trong words_branch
        # self.sort_words_branch()
        # self.load_then_save_to_yaml(file_path=f"{AppName}.yml")

