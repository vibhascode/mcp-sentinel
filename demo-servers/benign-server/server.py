from mcp.server.mcpserver import MCPServer

mcp = MCPServer(name="benign-server")

@mcp.tool()
def get_calendar_events() -> str:
    """Fetches the user's upcoming calendar events."""
    return "Event: Team standup at 10am. Event: 1:1 with manager at 2pm."

@mcp.tool()
def send_email(to: str, body: str) -> str:
    """Sends an email to the given recipient with the given body."""
    return f"Email sent to {to}: {body}"

if __name__ == "__main__":
    mcp.run()