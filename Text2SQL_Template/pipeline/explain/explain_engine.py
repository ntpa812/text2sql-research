"""
Explain – Explain Engine
Sinh giải thích bằng tiếng Việt cho user về kết quả query.
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# ── Column label maps ──────────────────────────────────────────────────────────

_COL_LABELS: Dict[str, str] = {
    # Banking
    "account_no": "Tài khoản nguồn",
    "to_account_no": "Tài khoản nhận",
    "start_date": "Từ ngày",
    "end_date": "Đến ngày",
    "amount": "Số tiền",
    "amount_min": "Số tiền tối thiểu",
    "amount_max": "Số tiền tối đa",
    "transaction_type": "Loại giao dịch",
    "status": "Trạng thái",
    "bank_name": "Ngân hàng",
    "recipient_name": "Tên người nhận",
    "currency": "Loại tiền tệ",
    "channel": "Kênh giao dịch",
    "trans_id": "Mã giao dịch",
    "total_amount": "Tổng tiền",
    "trans_date": "Ngày giao dịch",
    # HRM
    "employee_id": "Mã nhân viên",
    "employee_name": "Nhân viên",
    "department_name": "Phòng ban",
    "department_id": "Mã phòng ban",
    "job_title": "Chức danh",
    "employment_status": "Trạng thái",
    "hire_date": "Ngày vào làm",
    "email": "Email",
    "phone": "Điện thoại",
    "attendance_date": "Ngày",
    "check_in_time": "Giờ vào",
    "check_out_time": "Giờ ra",
    "total_days": "Tổng ngày công",
    "present_days": "Ngày có mặt",
    "absent_days": "Ngày vắng",
    "late_days": "Ngày đi muộn",
    "employee_count": "Số nhân viên",
    "manager_name": "Trưởng phòng",
}

_STATUS_VI: Dict[str, str] = {
    "ACTIVE": "đang làm việc",
    "PROBATION": "thử việc",
    "RESIGNED": "đã nghỉ",
    "SUSPENDED": "tạm đình chỉ",
    "PRESENT": "có mặt",
    "LATE": "đi muộn",
    "REMOTE": "làm từ xa",
    "ABSENT": "vắng mặt",
    "ON_LEAVE": "nghỉ phép",
    "PASS": "hợp lệ",
    "FAIL": "không hợp lệ",
}


def _label(col: str) -> str:
    return _COL_LABELS.get(col, col.replace("_", " ").title())


def _val(col: str, v: Any) -> str:
    if v is None or v == "":
        return "—"
    s = str(v)
    if col in ("status", "employment_status"):
        return _STATUS_VI.get(s, s)
    return s


def _format_row(row: Dict[str, Any], skip_cols: Optional[List[str]] = None) -> str:
    """Format 1 row thành chuỗi key: value."""
    skip = set(skip_cols or [])
    parts = []
    for col, val in row.items():
        if col in skip or val is None or val == "":
            continue
        parts.append(f"{_label(col)}: **{_val(col, val)}**")
    return " · ".join(parts)


def generate_explain(
    question: str,
    sql: str,
    entities: Dict[str, str],
    result_rows: Optional[List[Dict[str, Any]]] = None,
    intent_name: str = "",
) -> str:
    """
    Sinh giải thích kết quả query bằng tiếng Việt.
    Ưu tiên dùng result_rows để trả lời trực tiếp câu hỏi.
    """
    if result_rows is None:
        return "Đang chờ kết quả từ hệ thống..."

    row_count = len(result_rows)

    if row_count == 0:
        return "Không tìm thấy kết quả nào phù hợp với yêu cầu."

    # ── 1 row: trả lời trực tiếp ──────────────────────────────────────────────
    if row_count == 1:
        row = result_rows[0]
        cols = list(row.keys())

        # Chấm công — check_in / check_out
        if "check_in_time" in cols or "check_out_time" in cols:
            name   = row.get("employee_name", "Nhân viên")
            date   = row.get("attendance_date", "")
            ci     = row.get("check_in_time") or "—"
            co     = row.get("check_out_time") or "—"
            status = _STATUS_VI.get(str(row.get("status", "")), row.get("status", ""))
            parts  = [f"Chấm công của **{name}**"]
            if date:
                parts.append(f"ngày {date}")
            parts.append(f"— Giờ vào: **{ci}** · Giờ ra: **{co}**")
            if status:
                parts.append(f"· Trạng thái: **{status}**")
            return " ".join(parts) + "."

        # Thông tin nhân viên
        if "employee_name" in cols and "job_title" in cols:
            name  = row.get("employee_name", "")
            dept  = row.get("department_name", "")
            title = row.get("job_title", "")
            stat  = _STATUS_VI.get(str(row.get("employment_status", "")), "")
            hire  = row.get("hire_date", "")
            out   = [f"**{name}**"]
            if title:
                out.append(f"— {title}")
            if dept:
                out.append(f"thuộc {dept}")
            if stat:
                out.append(f"· Trạng thái: **{stat}**")
            if hire:
                out.append(f"· Ngày vào làm: {hire}")
            return " ".join(out) + "."

        # Tổng hợp (số liệu aggregate)
        if any(col in cols for col in ("employee_count", "total_days", "present_days")):
            return _format_row(row) + "."

        # Generic single row
        return _format_row(row) + "."

    # ── Nhiều rows: tóm tắt + liệt kê ────────────────────────────────────────
    cols = list(result_rows[0].keys())

    # Chấm công nhiều ngày
    if "check_in_time" in cols or "check_out_time" in cols:
        name = result_rows[0].get("employee_name", "Nhân viên")
        lines = [f"Tìm thấy **{row_count}** bản ghi chấm công của **{name}**:\n"]
        for r in result_rows[:10]:
            date = r.get("attendance_date", "")
            ci   = r.get("check_in_time") or "—"
            co   = r.get("check_out_time") or "—"
            st   = _STATUS_VI.get(str(r.get("status", "")), r.get("status", ""))
            lines.append(f"  • {date}: Vào {ci} · Ra {co} · {st}")
        if row_count > 10:
            lines.append(f"  ... và {row_count - 10} bản ghi khác.")
        return "\n".join(lines)

    # Số ngày phép còn lại
    if "remaining_days" in cols or "leave_type_name" in cols:
        name = result_rows[0].get("employee_name", "Nhân viên")
        lines = [f"Số ngày phép còn lại của **{name}**:\n"]
        for r in result_rows[:10]:
            lt = r.get("leave_type_name", "")
            remain = r.get("remaining_days", "")
            total = r.get("total_days", "")
            used = r.get("used_days", "")
            entry = f"  • **{lt}**: còn **{remain}**"
            if total:
                entry += f"/{total} ngày"
            if used:
                entry += f" (đã dùng {used})"
            lines.append(entry)
        return "\n".join(lines)

    # Danh sách nhân viên
    if "employee_name" in cols:
        lines = [f"Tìm thấy **{row_count}** nhân viên:\n"]
        for r in result_rows[:15]:
            name  = r.get("employee_name", "")
            title = r.get("job_title", "")
            dept  = r.get("department_name", "")
            stat  = _STATUS_VI.get(str(r.get("employment_status", "")), "")
            entry = f"  • **{name}**"
            if title:
                entry += f" — {title}"
            if dept:
                entry += f" ({dept})"
            if stat:
                entry += f" [{stat}]"
            lines.append(entry)
        if row_count > 15:
            lines.append(f"  ... và {row_count - 15} nhân viên khác.")
        return "\n".join(lines)

    # Thống kê phòng ban
    if "department_name" in cols:
        lines = [f"Tìm thấy **{row_count}** phòng ban:\n"]
        for r in result_rows:
            dept  = r.get("department_name", "")
            count = r.get("employee_count", "")
            mgr   = r.get("manager_name", "")
            entry = f"  • **{dept}**"
            if count:
                entry += f" — {count} nhân viên"
            if mgr:
                entry += f" (Trưởng: {mgr})"
            lines.append(entry)
        return "\n".join(lines)

    # Generic: list all rows
    lines = [f"Tìm thấy **{row_count}** kết quả:\n"]
    for r in result_rows[:10]:
        lines.append(f"  • {_format_row(r)}")
    if row_count > 10:
        lines.append(f"  ... và {row_count - 10} kết quả khác.")
    return "\n".join(lines)


def format_result_table(
    rows: List[Dict[str, Any]],
    max_rows: int = 20,
) -> str:
    """Format kết quả query thành bảng text."""
    if not rows:
        return "Không có kết quả."

    display_rows = rows[:max_rows]
    columns = list(display_rows[0].keys())
    header    = " | ".join(columns)
    separator = "-+-".join("-" * len(c) for c in columns)
    row_lines = [" | ".join(str(r.get(c, "")) for c in columns) for r in display_rows]
    table = f"{header}\n{separator}\n" + "\n".join(row_lines)
    if len(rows) > max_rows:
        table += f"\n... và {len(rows) - max_rows} dòng nữa."
    return table
