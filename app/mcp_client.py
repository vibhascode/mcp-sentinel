import sys
import yaml
from pathlib import Path
from contextlib import AsyncExitStack
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

CONFIG_PATH = Path(__file__).parent.parent / "mcp_servers.yaml"

with open(CONFIG_PATH) as f:
    _config = yaml.safe_load(f)

SERVERS = _config.get("servers", {})

_sessions: dict[str, ClientSession] = {}
_exit_stack = AsyncExitStack()


async def get_session(server_name: str) -> ClientSession:
    if server_name in _sessions:
        return _sessions[server_name]

    server_conf = SERVERS.get(server_name)
    if server_conf is None:
        raise ValueError(f"Unknown server_name '{server_name}' — check mcp_servers.yaml")

    params = StdioServerParameters(
        command=sys.executable,   # <-- use the SAME interpreter running this process
        args=server_conf["args"],
    )

    read_stream, write_stream = await _exit_stack.enter_async_context(stdio_client(params))
    session = await _exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
    await session.initialize()

    _sessions[server_name] = session
    return session

async def list_tools(server_name: str) -> list[dict]:
    """Returns tool defs in the same shape fingerprint.py expects."""
    session = await get_session(server_name)
    result = await session.list_tools()
    return [
        {"name": t.name, "description": t.description, "inputSchema": t.inputSchema}
        for t in result.tools
    ]


async def call_tool(server_name: str, tool_name: str, tool_args: dict) -> dict:
    """Actually invokes the tool on the real MCP server, returns its result."""
    session = await get_session(server_name)
    result = await session.call_tool(tool_name, tool_args)
    # MCP responses are a list of content blocks; flatten text blocks for now
    text_parts = [c.text for c in result.content if hasattr(c, "text")]
    return {"status": "executed", "tool": tool_name, "output": "\n".join(text_parts)}


async def shutdown():
    """Call on app shutdown to cleanly close all server subprocesses."""
    await _exit_stack.aclose()