import sys
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uuid
import yaml
import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.db import init_db, log_audit, get_conn
from app.intent import start_session, check_intent
from app.fingerprint import check_fingerprint
from app.provenance import tag_output, check_taint
from app.risk_engine import decide
from app import mcp_client

app = FastAPI(title="MCP Sentinel Gateway")

CONFIG_PATH = Path(__file__).parent.parent / "mcp_servers.yaml"
with open(CONFIG_PATH) as f:
    _config = yaml.safe_load(f)

PRIVILEGED_TOOLS = _config.get("privileged_tools", [])
SERVER_TRUST = {name: conf["trust_level"] for name, conf in _config.get("servers", {}).items()}


@app.on_event("startup")
def on_startup():
    init_db()


@app.on_event("shutdown")
async def on_shutdown():
    await mcp_client.shutdown()


class StartSessionRequest(BaseModel):
    original_intent: str
    agent_label: str = "unknown"

class StartSessionResponse(BaseModel):
    session_id: str

class ToolCallRequest(BaseModel):
    session_id: str
    server_name: str
    tool_name: str
    tool_args: dict

class ToolCallResponse(BaseModel):
    decision: str
    reasons: list[str]
    result: dict | None = None


@app.post("/session/start", response_model=StartSessionResponse)
def session_start(req: StartSessionRequest):
    session_id = str(uuid.uuid4())
    start_session(session_id, req.original_intent)
    return StartSessionResponse(session_id=session_id)


@app.post("/tool/call", response_model=ToolCallResponse)
async def tool_call(req: ToolCallRequest):
    if req.server_name not in SERVER_TRUST:
        raise HTTPException(status_code=400, detail=f"Unknown server_name '{req.server_name}'")
    trust_level = SERVER_TRUST[req.server_name]

    # fetch the REAL tool definition from the server ourselves — never trust
    # a client-supplied tool_def, or fingerprinting is trivially bypassable
    available_tools = await mcp_client.list_tools(req.server_name)
    tool_def = next((t for t in available_tools if t["name"] == req.tool_name), None)
    if tool_def is None:
        raise HTTPException(status_code=404, detail=f"Tool '{req.tool_name}' not found on server '{req.server_name}'")

    fp_result = check_fingerprint(req.server_name, tool_def)

    try:
        intent_result = check_intent(req.session_id, req.tool_name, req.tool_args)
    except ValueError:
        raise HTTPException(status_code=404, detail="Unknown session_id")

    taint_result = check_taint(req.session_id, req.tool_name, req.tool_args, PRIVILEGED_TOOLS)

    verdict = decide(fp_result, intent_result, taint_result)

    log_audit(req.session_id, req.tool_name, verdict["decision"], verdict["reasons"])

    result = None
    if verdict["decision"] == "ALLOW":
        result = await mcp_client.call_tool(req.server_name, req.tool_name, req.tool_args)
        tag_output(req.session_id, req.tool_name, req.server_name, trust_level, result.get("output"))

    return ToolCallResponse(
        decision=verdict["decision"],
        reasons=verdict["reasons"],
        result=result,
    )


@app.get("/api/logs")
def get_logs(limit: int = 50):
    conn = get_conn()
    rows = conn.execute("""
        SELECT id, session_id, tool_name, decision, reasons, created_at
        FROM audit_log
        ORDER BY id DESC
        LIMIT ?
    """, (limit,)).fetchall()
    conn.close()
    return {
        "logs": [
            {
                "id": row["id"],
                "session_id": row["session_id"],
                "tool_name": row["tool_name"],
                "decision": row["decision"],
                "reasons": json.loads(row["reasons"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    }


@app.get("/api/stats")
def get_stats():
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) as c FROM audit_log").fetchone()["c"]
    blocked = conn.execute("SELECT COUNT(*) as c FROM audit_log WHERE decision = 'BLOCK'").fetchone()["c"]
    allowed = conn.execute("SELECT COUNT(*) as c FROM audit_log WHERE decision = 'ALLOW'").fetchone()["c"]
    ask_user = conn.execute("SELECT COUNT(*) as c FROM audit_log WHERE decision = 'ASK_USER'").fetchone()["c"]
    conn.close()
    return {
        "total_actions": total,
        "allowed": allowed,
        "flagged_for_review": ask_user,
        "blocked": blocked,
    }