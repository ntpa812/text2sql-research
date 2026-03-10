"""
Template Store – Template Loader
Load SQL templates đã approved từ thư mục approved_templates/ và từ intent dataset.
"""

import os
import glob
import logging
from typing import Dict, Optional, List, Any

from config.settings import APPROVED_TEMPLATES_DIR

logger = logging.getLogger(__name__)


def load_approved_templates() -> Dict[str, str]:
    """
    Load tất cả .sql files từ approved_templates/.
    Returns: { "template_id": "SELECT ... FROM ..." }
    """
    templates: Dict[str, str] = {}
    pattern = os.path.join(APPROVED_TEMPLATES_DIR, "*.sql")

    for filepath in glob.glob(pattern):
        template_id = os.path.splitext(os.path.basename(filepath))[0]
        with open(filepath, "r", encoding="utf-8") as f:
            sql = f.read().strip()
        if sql:
            templates[template_id] = sql
            logger.debug(f"[Template] Loaded: {template_id}")

    logger.info(f"[Template] Loaded {len(templates)} approved templates.")
    return templates


def get_template_for_intent(
    intent: Dict[str, Any],
    approved_templates: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    """
    Lấy template SQL phù hợp với intent.
    Ưu tiên:
      1. Approved template file (nếu có match intent_id)
      2. SQL template từ intent dataset (metadata field)
    """
    intent_id = intent.get("intent_id", "")

    # 1. Tìm trong approved templates
    if approved_templates:
        if intent_id in approved_templates:
            logger.info(f"[Template] Using approved template: {intent_id}")
            return approved_templates[intent_id]

        # Fuzzy match: tìm template chứa intent_id
        for tid, sql in approved_templates.items():
            if intent_id in tid or tid in intent_id:
                logger.info(f"[Template] Fuzzy match: {tid} for intent {intent_id}")
                return sql

    # 2. Fallback: dùng SQL từ intent metadata
    sql_template = intent.get("sql_template", "")
    if sql_template:
        logger.info(f"[Template] Using intent metadata SQL for: {intent_id}")
        return sql_template

    return None


def save_approved_template(intent_id: str, sql: str) -> str:
    """
    Lưu template SQL đã validated thành approved template.
    Dùng sau khi chạy thành công để tích lũy templates tốt.
    """
    os.makedirs(APPROVED_TEMPLATES_DIR, exist_ok=True)
    filepath = os.path.join(APPROVED_TEMPLATES_DIR, f"{intent_id}.sql")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(sql)
    logger.info(f"[Template] Saved approved template: {filepath}")
    return filepath
