import sys
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("test")

@mcp.tool()
def ping() -> str:
    return "PONG from test server"

if __name__ == "__main__":
    print("TEST SERVER STARTING", file=sys.stderr)
    mcp.run()