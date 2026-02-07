import asyncio

from dedalus_mcp import MCPServer, tool


@tool(description="Echo a message back to the caller")
def echo(message: str) -> str:
    return message


@tool(description="Open a URL in the chaos runner (placeholder)")
def open_url(url: str) -> str:
    # Wire this to Playwright/ChaosMonkey if you want real actions.
    return f"Requested open_url: {url}"


server = MCPServer("mayhem-monkey")
server.collect(echo, open_url)


if __name__ == "__main__":
    asyncio.run(server.serve())
