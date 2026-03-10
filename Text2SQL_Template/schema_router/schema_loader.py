"""
Schema Router – Schema Loader
Load semantic profiles (JSON) từ thư mục data/semantic_profiles/.
Cung cấp metadata cho các module khác.
"""

import json
import os
import glob
from typing import Dict, List, Any

from config.settings import SEMANTIC_PROFILES_DIR


def load_all_profiles() -> Dict[str, Any]:
    """
    Load tất cả semantic profile JSON files.
    Returns: { table_name: { "columns": [...], ... } }
    """
    profiles: Dict[str, Any] = {}
    pattern = os.path.join(SEMANTIC_PROFILES_DIR, "*.json")

    for filepath in glob.glob(pattern):
        with open(filepath, "r", encoding="utf-8") as f:
            profile = json.load(f)
        table_name = profile.get("table_name", os.path.splitext(os.path.basename(filepath))[0])
        profiles[table_name] = profile

    return profiles


def get_schema_description(profiles: Dict[str, Any], table_names: List[str] | None = None) -> str:
    """
    Sinh schema description text cho LLM prompt.
    Nếu table_names = None → dùng tất cả.
    """
    if table_names is None:
        table_names = list(profiles.keys())

    lines: List[str] = []
    for tname in table_names:
        profile = profiles.get(tname)
        if not profile:
            continue
        cols = profile.get("columns", [])
        col_strs = [f"  {c['name']} ({c.get('role', '')})" for c in cols]
        lines.append(f"{tname}(")
        lines.extend(col_strs)
        lines.append(")")
        lines.append("")

    return "\n".join(lines)


def get_column_names(profiles: Dict[str, Any], table_name: str) -> List[str]:
    """Trả về danh sách tên cột của một bảng."""
    profile = profiles.get(table_name, {})
    return [c["name"] for c in profile.get("columns", [])]


def get_all_table_names(profiles: Dict[str, Any]) -> List[str]:
    return list(profiles.keys())
