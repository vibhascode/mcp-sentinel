import sys
import asyncio
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uuid
import yaml
from pathlib import Path
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.db import init_db
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

    result = None
    if verdict["decision"] == "ALLOW":
        result = await mcp_client.call_tool(req.server_name, req.tool_name, req.tool_args)
        tag_output(req.session_id, req.tool_name, req.server_name, trust_level, result.get("output"))

    return ToolCallResponse(
        decision=verdict["decision"],
        reasons=verdict["reasons"],
        result=result,
    )