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

from domain_router.registry_loader import load_domain_registry
from pipeline.pipeline_runner import run_pipeline
from sql_generation.llm_sql_generator import get_generation_config

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR / "demo_ui" / "dist"
HRM_DB_PATH = BASE_DIR / "data" / "mock" / "hrm.db"


def _hrm_query(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(HRM_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()

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
