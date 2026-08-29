import asyncio
from app.mcp_client import list_tools, call_tool, shutdown

async def main():
    tools = await list_tools("benign")
    print("Tools:", tools)

    result = await call_tool("benign", "get_calendar_events", {"date": "tomorrow"})
    print("Result:", result)

    await shutdown()

asyncio.run(main())