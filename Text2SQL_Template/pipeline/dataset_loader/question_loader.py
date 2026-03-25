"""
Dataset Loader – Question Loader
Đọc user questions từ nhiều format (json, csv, xlsx, md) và normalize về list chuẩn.
"""

import json
import os
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def load_questions(path: str) -> List[Dict[str, Any]]:
    """
    Load questions từ file, trả về list dạng chuẩn:
    [{"id": "q001", "question": "...", ...}, ...]

    Hỗ trợ: .json, .csv, .xlsx, .md
    Các field phụ (expected_intent, expected_entities) giữ nguyên nếu có.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Không tìm thấy file: {path}")

    ext = os.path.splitext(path)[1].lower()

    if ext == ".json":
        return _load_json(path)
    elif ext == ".csv":
        return _load_csv(path)
    elif ext in (".xlsx", ".xls"):
        return _load_xlsx(path)
    elif ext == ".md":
        return _load_md(path)
    else:
        raise ValueError(f"Format không được hỗ trợ: {ext}. Dùng .json / .csv / .xlsx / .md")


def _load_json(path: str) -> List[Dict[str, Any]]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        results = []
        for i, item in enumerate(data):
            if isinstance(item, dict) and "question" in item:
                item.setdefault("id", f"q{i+1:03d}")
                results.append(item)
            elif isinstance(item, str):
                results.append({"id": f"q{i+1:03d}", "question": item})
        return results
    else:
        raise ValueError("JSON phải là list of objects hoặc list of strings")


def _load_csv(path: str) -> List[Dict[str, Any]]:
    import csv

    results = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            question = row.get("question", "").strip()
            if not question:
                continue
            entry = {
                "id": row.get("id", f"q{i+1:03d}"),
                "question": question,
            }
            if row.get("expected_intent"):
                entry["expected_intent"] = row["expected_intent"].strip()
            if row.get("expected_entities"):
                try:
                    entry["expected_entities"] = json.loads(row["expected_entities"])
                except (json.JSONDecodeError, TypeError):
                    pass
            results.append(entry)
    return results


def _load_xlsx(path: str) -> List[Dict[str, Any]]:
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("Cần cài pandas + openpyxl: pip install pandas openpyxl")

    df = pd.read_excel(path, engine="openpyxl")

    if "question" not in df.columns:
        raise ValueError("File xlsx phải có cột 'question'")

    results = []
    for i, row in df.iterrows():
        question = str(row["question"]).strip()
        if not question or question == "nan":
            continue
        entry = {
            "id": str(row.get("id", f"q{i+1:03d}")),
            "question": question,
        }
        if "expected_intent" in df.columns and pd.notna(row.get("expected_intent")):
            entry["expected_intent"] = str(row["expected_intent"]).strip()
        results.append(entry)
    return results


def _load_md(path: str) -> List[Dict[str, Any]]:
    results = []
    with open(path, encoding="utf-8") as f:
        idx = 0
        for line in f:
            line = line.strip()
            if line.startswith("- "):
                question = line[2:].strip()
                if question:
                    idx += 1
                    results.append({"id": f"q{idx:03d}", "question": question})
    return results


def save_processed(questions: List[Dict[str, Any]], output_path: str):
    """Lưu questions đã normalize ra file JSON chuẩn."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=2)
    logger.info(f"Đã lưu {len(questions)} questions vào {output_path}")
