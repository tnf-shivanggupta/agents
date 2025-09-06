from mcp.server.fastmcp import FastMCP

mcp = FastMCP("stripe_tools_server")

@mcp.tool()
async def get_pi_status(id: str) -> str:
    """Get the status of stripe payment intent.

    Args:
        id: The id of the stripe payment intent
    """
    res = f"Status of payment intent - {id} - is 'succeeded'"
    return res

if __name__ == "__main__":
    mcp.run(transport='stdio')