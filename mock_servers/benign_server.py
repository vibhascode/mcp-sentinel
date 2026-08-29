from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import asyncio
import json

app = Server("benign-server")

@app.list_tools()
async def list_tools():
    return [
        Tool(
            name="get_calendar_events",
            description="Fetch calendar events for a given date",
            inputSchema={
                "type": "object",
                "properties": {"date": {"type": "string"}},
                "required": ["date"],
            },
        ),
        Tool(
            name="transfer_funds",
            description="Transfer funds to a specified account",
            inputSchema={
                "type": "object",
                "properties": {"amount": {"type": "string"}},
                "required": ["amount"],
            },
        ),
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    if name == "get_calendar_events":
        events = [{"title": "Team standup", "time": "10:00"}, {"title": "Lunch", "time": "13:00"}]
        return [TextContent(type="text", text=json.dumps(events))]
    if name == "transfer_funds":
        return [TextContent(type="text", text=f"Transferred: {arguments.get('amount')}")]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())