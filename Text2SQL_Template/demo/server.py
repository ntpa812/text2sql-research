"""
Demo server cho UI chatbot Text2SQL.
Chay API demo mode, bo qua DB that va tra ve debug context day du.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from pipeline.domain_router.registry_loader import load_domain_registry
from pipeline.runner import run_pipeline
from pipeline.sql_generation.llm_sql_generator import get_generation_config

BASE_DIR = Path(__file__).resolve().parent.parent  # project root
FRONTEND_DIST = BASE_DIR / "demo" / "ui" / "dist"
HRM_DB_PATH     = BASE_DIR / "data" / "domains" / "hrm"     / "mock" / "hrm.db"
BANKING_DB_PATH = BASE_DIR / "data" / "domains" / "banking" / "mock" / "banking.db"


def _db_query(db_path: Path, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def _hrm_query(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    return _db_query(HRM_DB_PATH, sql, params)


def _banking_query(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    return _db_query(BANKING_DB_PATH, sql, params)

app = FastAPI(title="Text2SQL Demo API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    forced_domain: str | None = None
    use_embedding: bool = False


def _build_assistant_message(result: Dict[str, Any]) -> str:
    if result.get("error"):
        return (
            f"Khong the hoan tat truy van. "
            f"Trang thai: {result.get('validator', 'FAIL')}. "
            f"Chi tiet: {result['error']}"
        )

    explain = result.get("explain", "").strip()
    if explain:
        return explain

    rows = result.get("rows", 0)
    domain = result.get("domain", "unknown")
    intent = result.get("intent_name") or result.get("intent") or "chua xac dinh"
    return (
        f"Da route sang domain `{domain}` voi intent `{intent}`. "
        f"SQL da duoc tao thanh cong va hien co {rows} dong du lieu demo."
    )


@app.get("/api/meta")
def get_meta():
    registry = load_domain_registry()
    return {
        "models": get_generation_config(),
        "domains": [
            {
                "domain_id": item["domain_id"],
                "display_name": item.get("display_name", item["domain_id"]),
                "description": item.get("description", ""),
            }
            for item in registry.get("domains", {}).values()
        ],
    }


@app.post("/api/chat")
def chat(req: ChatRequest):
    result = run_pipeline(
        req.message,
        use_embedding=req.use_embedding,
        explain=True,
        forced_domain=req.forced_domain,
        demo_mode=True,
    )
    return {
        "assistant_message": _build_assistant_message(result),
        "result": result,
    }


@app.get("/api/hrm/departments")
def hrm_departments():
    rows = _hrm_query("""
        SELECT d.department_id, d.department_name, d.manager_id,
               e.employee_name AS manager_name,
               COUNT(emp.employee_id) AS employee_count
        FROM department d
        LEFT JOIN employee e ON d.manager_id = e.employee_id
        LEFT JOIN employee emp ON emp.department_id = d.department_id
        GROUP BY d.department_id
        ORDER BY d.department_id
    """)
    return {"departments": rows}


@app.get("/api/hrm/employees")
def hrm_employees(
    department_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    where = "WHERE 1=1"
    params: list = []
    if department_id:
        where += " AND e.department_id = ?"
        params.append(department_id)
    if status:
        where += " AND e.employment_status = ?"
        params.append(status)
    rows = _hrm_query(f"""
        SELECT e.employee_id, e.employee_name, d.department_name,
               e.job_title, e.employment_status, e.hire_date, e.email, e.phone
        FROM employee e
        JOIN department d ON e.department_id = d.department_id
        {where}
        ORDER BY e.department_id, e.employee_name
    """, tuple(params))
    return {"employees": rows}


@app.get("/api/hrm/attendance")
def hrm_attendance(
    date_from: str = Query(default="2026-03-01"),
    date_to: str = Query(default="2026-03-24"),
):
    rows = _hrm_query("""
        SELECT a.attendance_date, a.employee_id, e.employee_name,
               d.department_name, a.check_in_time, a.check_out_time, a.status
        FROM attendance a
        JOIN employee e ON a.employee_id = e.employee_id
        JOIN department d ON e.department_id = d.department_id
        WHERE a.attendance_date BETWEEN ? AND ?
        ORDER BY a.attendance_date DESC, e.department_id
        LIMIT 300
    """, (date_from, date_to))
    return {"attendance": rows, "date_from": date_from, "date_to": date_to}


# ── Banking endpoints ──────────────────────────────────────────────────────────

@app.get("/api/banking/customers")
def banking_customers():
    rows = _banking_query("""
        SELECT c.cif_no, c.customer_no, c.customer_name, c.mobile_phone, c.email,
               c.status,
               COUNT(a.id) AS account_count
        FROM customer c
        LEFT JOIN customer_account a ON c.customer_no = a.customer_no
        GROUP BY c.id
        ORDER BY c.customer_name
    """)
    return {"customers": rows}


@app.get("/api/banking/accounts")
def banking_accounts(
    customer_no: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
):
    where = "WHERE 1=1"
    params: list = []
    if customer_no:
        where += " AND a.customer_no = ?"
        params.append(customer_no)
    if status:
        where += " AND a.status = ?"
        params.append(status)
    rows = _banking_query(f"""
        SELECT a.account_no, a.customer_no, c.customer_name, a.account_class,
               a.account_name, a.status, a.create_date
        FROM customer_account a
        JOIN customer c ON a.customer_no = c.customer_no
        {where}
        ORDER BY a.customer_no, a.account_class
    """, tuple(params))
    return {"accounts": rows}


@app.get("/api/banking/transactions")
def banking_transactions(
    account_no: Optional[str] = Query(default=None),
    trans_type: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    date_from: str = Query(default="2026-03-01"),
    date_to: str = Query(default="2026-03-31"),
):
    where = "WHERE t.trans_time BETWEEN ? AND ?"
    params: list = [date_from + " 00:00:00", date_to + " 23:59:59"]
    if account_no:
        where += " AND (t.from_account_no = ? OR t.to_account_no = ?)"
        params += [account_no, account_no]
    if trans_type:
        where += " AND t.trans_type = ?"
        params.append(trans_type)
    if status:
        where += " AND t.trans_status = ?"
        params.append(status)
    rows = _banking_query(f"""
        SELECT t.trans_id, t.trans_time, t.trans_type, t.trans_name,
               t.from_account_no, t.to_account_no, t.to_account_fullname,
               t.amount_transfer, t.amount_currency, t.fee_amount,
               t.trans_status, t.channel_receiver, t.trans_desc
        FROM "transaction" t
        {where}
        ORDER BY t.trans_time DESC
        LIMIT 300
    """, tuple(params))
    return {
        "transactions": rows,
        "date_from": date_from,
        "date_to": date_to,
    }


@app.get("/api/banking/summary")
def banking_summary(
    date_from: str = Query(default="2026-03-01"),
    date_to: str = Query(default="2026-03-31"),
):
    params = (date_from + " 00:00:00", date_to + " 23:59:59")
    by_type = _banking_query("""
        SELECT trans_type,
               COUNT(*) AS count,
               SUM(amount_transfer) AS total_amount,
               SUM(CASE WHEN trans_status='SUCCESS' THEN 1 ELSE 0 END) AS success_count
        FROM "transaction"
        WHERE trans_time BETWEEN ? AND ?
        GROUP BY trans_type
        ORDER BY total_amount DESC
    """, params)
    by_channel = _banking_query("""
        SELECT channel_receiver,
               COUNT(*) AS count,
               SUM(amount_transfer) AS total_amount
        FROM "transaction"
        WHERE trans_time BETWEEN ? AND ?
        GROUP BY channel_receiver
        ORDER BY count DESC
    """, params)
    return {"by_type": by_type, "by_channel": by_channel, "date_from": date_from, "date_to": date_to}


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")


@app.get("/")
def serve_index():
    index_file = FRONTEND_DIST / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "message": "Frontend chua build. Chay npm trong demo_ui/ de xem giao dien."
    }
