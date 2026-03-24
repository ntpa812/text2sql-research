"""
Template Store – Template Loader
Load SQL templates đã approved từ thư mục approved_templates/ và từ intent dataset.
"""

import os
import glob
import logging
from typing import Dict, Optional, List, Any

from config.settings import DEFAULT_DOMAIN_ID, LEGACY_APPROVED_TEMPLATES_DIR

logger = logging.getLogger(__name__)


def _resolve_templates_dir(path: str | None = None, domain_id: str | None = None) -> str:
    if path:
        return path

    domain_id = domain_id or DEFAULT_DOMAIN_ID
    domain_candidate = os.path.join(
        os.path.dirname(LEGACY_APPROVED_TEMPLATES_DIR),
        domain_id,
        os.path.basename(LEGACY_APPROVED_TEMPLATES_DIR),
    )
    if os.path.isdir(domain_candidate):
        return domain_candidate
    return LEGACY_APPROVED_TEMPLATES_DIR


def load_approved_templates(path: str | None = None, domain_id: str | None = None) -> Dict[str, str]:
    """
    Load tất cả .sql files từ approved_templates/.
    Returns: { "template_id": "SELECT ... FROM ..." }
    """
    templates: Dict[str, str] = {}
    pattern = os.path.join(_resolve_templates_dir(path, domain_id), "*.sql")

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


def save_approved_template(intent_id: str, sql: str, path: str | None = None, domain_id: str | None = None) -> str:
    """
    Lưu template SQL đã validated thành approved template.
    Dùng sau khi chạy thành công để tích lũy templates tốt.
    """
    target_dir = _resolve_templates_dir(path, domain_id)
    os.makedirs(target_dir, exist_ok=True)
    filepath = os.path.join(target_dir, f"{intent_id}.sql")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(sql)
    logger.info(f"[Template] Saved approved template: {filepath}")
    return filepath
