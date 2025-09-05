# product_mcp_server.py
from mcp.server.fastmcp import FastMCP
import requests
import json

mcp = FastMCP("ProductAgent",
              instructions="You are answering every question about financial products.",
              host="localhost",
              port=8004)

@mcp.tool()
def get_products() -> str:
    """
    Get all available financial products including credit cards, savings accounts, and loans.
    This tool fetches product data from the data server.
    """
    try:
        resp = requests.get("http://localhost:8000/products")
        resp.raise_for_status()
        data = resp.json()
        return json.dumps(data, indent=2, ensure_ascii=False)
    except Exception as e:
        return f"Error getting products: {e}"

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
