"""
Explain – Explain Engine
Sinh giải thích bằng tiếng Việt cho user về kết quả query.
"""

import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


def generate_explain(
    question: str,
    sql: str,
    entities: Dict[str, str],
    result_rows: Optional[List[Dict[str, Any]]] = None,
    intent_name: str = "",
) -> str:
    """
    Sinh giải thích kết quả query bằng tiếng Việt.
    """
    parts: List[str] = []

    parts.append("Hệ thống đã thực hiện tra cứu với các điều kiện:")

    # Liệt kê entities đã dùng
    entity_labels = {
        "account_no": "tài khoản nguồn",
        "to_account_no": "tài khoản nhận",
        "start_date": "từ ngày",
        "end_date": "đến ngày",
        "amount": "số tiền",
        "amount_min": "số tiền tối thiểu",
        "amount_max": "số tiền tối đa",
        "transaction_type": "loại giao dịch",
        "status": "trạng thái",
        "bank_name": "ngân hàng",
        "recipient_name": "tên người nhận",
        "currency": "loại tiền tệ",
        "channel": "kênh giao dịch",
        "trans_id": "mã giao dịch",
    }

    for key, value in entities.items():
        label = entity_labels.get(key, key)
        parts.append(f"  - {label}: {value}")

    # Kết quả
    if result_rows is not None:
        row_count = len(result_rows)
        if row_count == 0:
            parts.append("\nKết quả: Không tìm thấy giao dịch nào phù hợp.")
        else:
            parts.append(f"\nKết quả: Tìm thấy {row_count} giao dịch.")
    else:
        parts.append("\nĐang chờ kết quả từ hệ thống...")

    return "\n".join(parts)


def format_result_table(
    rows: List[Dict[str, Any]],
    max_rows: int = 20,
) -> str:
    """
    Format kết quả query thành bảng text.
    """
    if not rows:
        return "Không có kết quả."

    display_rows = rows[:max_rows]
    columns = list(display_rows[0].keys())

    # Header
    header = " | ".join(columns)
    separator = "-+-".join("-" * len(c) for c in columns)

    # Rows
    row_lines = []
    for row in display_rows:
        values = [str(row.get(c, "")) for c in columns]
        row_lines.append(" | ".join(values))

    table = f"{header}\n{separator}\n" + "\n".join(row_lines)

    if len(rows) > max_rows:
        table += f"\n... và {len(rows) - max_rows} dòng nữa."

    return table
