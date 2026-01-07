"""
Unicode Normalization Utilities

Module này cung cấp các hàm chuẩn hóa Unicode để đảm bảo tính nhất quán
khi lưu trữ và so sánh dữ liệu trong database.

Sử dụng NFC (Canonical Decomposition, followed by Canonical Composition) là tiêu chuẩn
được khuyến nghị cho lưu trữ và so sánh text, đặc biệt quan trọng với tiếng Việt.

Ví dụ:
    - "Từ" có thể được biểu diễn dưới dạng NFC (1 ký tự đã composed) hoặc NFD (base + combining marks)
    - Hai dạng này nhìn giống nhau nhưng binary khác nhau
    - Nếu không chuẩn hóa, việc tìm kiếm/so sánh sẽ thất bại

Usage:
    from core.unicode_utils import normalize_text, normalize_dict, normalize_for_db

    # Chuẩn hóa một chuỗi
    text = normalize_text("Điều 1. Giải thích từ ngữ")

    # Chuẩn hóa toàn bộ dict/metadata
    metadata = normalize_dict({"title": "Quy định về...", "intent": "Chính sách"})

    # Chuẩn hóa nhiều giá trị cùng lúc
    question, answer = normalize_for_db(question, answer)
"""

import unicodedata
from typing import Any, Dict, List, Optional, Union, overload


@overload
def normalize_text(text: str, form: str = 'NFC') -> str: ...
@overload
def normalize_text(text: None, form: str = 'NFC') -> None: ...
@overload
def normalize_text(text: Optional[str], form: str = 'NFC') -> Optional[str]: ...

def normalize_text(text: Optional[str], form: str = 'NFC') -> Optional[str]:
    """
    Chuẩn hóa Unicode cho một chuỗi text.

    Args:
        text: Chuỗi cần chuẩn hóa. Nếu None sẽ trả về None.
        form: Dạng chuẩn hóa ('NFC', 'NFD', 'NFKC', 'NFKD'). Mặc định 'NFC'.
              - NFC: Canonical Decomposition + Canonical Composition (khuyến nghị)
              - NFD: Canonical Decomposition
              - NFKC: Compatibility Decomposition + Canonical Composition
              - NFKD: Compatibility Decomposition

    Returns:
        Chuỗi đã được chuẩn hóa, hoặc None nếu input là None.

    Example:
        >>> normalize_text("Việt Nam")  # Đảm bảo dạng NFC
        'Việt Nam'
    """
    if text is None:
        return None
    if not isinstance(text, str):
        return text
    return unicodedata.normalize(form, text)


def normalize_dict(data: Dict[str, Any], form: str = 'NFC') -> Dict[str, Any]:
    """
    Chuẩn hóa Unicode cho tất cả các giá trị string trong dict (recursive).

    Args:
        data: Dict cần chuẩn hóa
        form: Dạng chuẩn hóa Unicode

    Returns:
        Dict mới với tất cả string values đã được chuẩn hóa

    Example:
        >>> normalize_dict({"title": "Quy định", "count": 5})
        {'title': 'Quy định', 'count': 5}
    """
    if data is None:
        return {}
    if not isinstance(data, dict):
        return data

    result = {}
    for key, value in data.items():
        # Chuẩn hóa key nếu là string
        normalized_key = normalize_text(key, form) if isinstance(key, str) else key

        # Chuẩn hóa value dựa trên type
        if isinstance(value, str):
            result[normalized_key] = normalize_text(value, form)
        elif isinstance(value, dict):
            result[normalized_key] = normalize_dict(value, form)
        elif isinstance(value, list):
            result[normalized_key] = normalize_list(value, form)
        else:
            result[normalized_key] = value

    return result


def normalize_list(data: Optional[List[Any]], form: str = 'NFC') -> Optional[List[Any]]:
    """
    Chuẩn hóa Unicode cho tất cả các phần tử string trong list (recursive).

    Args:
        data: List cần chuẩn hóa
        form: Dạng chuẩn hóa Unicode

    Returns:
        List mới với tất cả string elements đã được chuẩn hóa
    """
    if data is None:
        return None
    if not isinstance(data, list):
        return data

    result = []
    for item in data:
        if isinstance(item, str):
            result.append(normalize_text(item, form))
        elif isinstance(item, dict):
            result.append(normalize_dict(item, form))
        elif isinstance(item, list):
            result.append(normalize_list(item, form))
        else:
            result.append(item)

    return result


def normalize_for_db(*args: Optional[str], form: str = 'NFC') -> tuple:
    """
    Chuẩn hóa Unicode cho nhiều giá trị cùng lúc (tiện dụng cho database operations).

    Args:
        *args: Các chuỗi cần chuẩn hóa
        form: Dạng chuẩn hóa Unicode

    Returns:
        Tuple các chuỗi đã được chuẩn hóa

    Example:
        >>> question, answer = normalize_for_db(question, answer)
        >>> heading, text, intent = normalize_for_db(heading, text, intent)
    """
    return tuple(normalize_text(arg, form) for arg in args)


def normalize_chunk_for_db(chunk: Dict[str, Any], form: str = 'NFC') -> Dict[str, Any]:  # type: ignore
    """
    Chuẩn hóa Unicode cho một chunk object (dùng trong RAG).

    Chuẩn hóa các trường text quan trọng:
    - text
    - metadata.heading
    - metadata.parent_heading
    - metadata.full_path
    - metadata.contextual_text
    - metadata.section_summary

    Args:
        chunk: Dict chứa chunk data
        form: Dạng chuẩn hóa Unicode

    Returns:
        Chunk mới với các trường text đã được chuẩn hóa
    """
    if chunk is None:
        return {}

    result = chunk.copy()

    # Chuẩn hóa text chính
    if 'text' in result:
        result['text'] = normalize_text(result['text'], form)

    # Chuẩn hóa metadata
    if 'metadata' in result and isinstance(result['metadata'], dict):
        metadata = result['metadata'].copy()

        text_fields = [
            'heading', 'parent_heading', 'full_path',
            'contextual_text', 'section_summary', 'title',
            'original_filename', 'document_path'
        ]

        for field in text_fields:
            if field in metadata and isinstance(metadata[field], str):
                metadata[field] = normalize_text(metadata[field], form)

        # Chuẩn hóa children_headings nếu là list
        if 'children_headings' in metadata and isinstance(metadata['children_headings'], list):
            metadata['children_headings'] = [
                normalize_text(h, form) if isinstance(h, str) else h
                for h in metadata['children_headings']
            ]

        result['metadata'] = metadata

    return result


def normalize_metadata_for_db(metadata: Dict[str, Any], form: str = 'NFC') -> Dict[str, Any]:
    """
    Chuẩn hóa Unicode cho metadata dict (dùng khi insert vào database).

    Args:
        metadata: Dict metadata cần chuẩn hóa
        form: Dạng chuẩn hóa Unicode

    Returns:
        Metadata mới đã được chuẩn hóa
    """
    return normalize_dict(metadata, form)


# Alias cho compatibility
nfc = lambda text: normalize_text(text, 'NFC')
nfd = lambda text: normalize_text(text, 'NFD')
nfkc = lambda text: normalize_text(text, 'NFKC')
nfkd = lambda text: normalize_text(text, 'NFKD')
