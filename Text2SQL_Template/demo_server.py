"""
Demo server cho UI chatbot Text2SQL.
Chay API demo mode, bo qua DB that va tra ve debug context day du.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from domain_router.registry_loader import load_domain_registry
from pipeline.pipeline_runner import run_pipeline
from sql_generation.llm_sql_generator import get_generation_config

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = BASE_DIR / "demo_ui" / "dist"

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
