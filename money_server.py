# money_mcp_server.py
from mcp.server.fastmcp import FastMCP
import requests
import json

mcp = FastMCP("MoneyAgent",
              instructions="You are answering every question about money.",
              host="localhost",
              port=8003)

@mcp.tool()
def get_money_info(user_id: str = "1414141") -> str:
    """
    Get comprehensive financial information for a user including credit data, balance information, and transaction history.
    This tool fetches data from multiple endpoints to provide complete financial overview.
    User ID is optional - if not provided, uses the default hardcoded user.
    """
    try:
        # Always use hardcoded user ID regardless of what was passed
        user_id = "1414141"  # Hardcoded for now
        endpoints = [
            f"http://localhost:8000/credit/{user_id}",
            f"http://localhost:8000/balance/{user_id}",
            f"http://localhost:8000/transaction/{user_id}"
        ]
        
        all_data = {}
        
        for endpoint in endpoints:
            try:
                resp = requests.get(endpoint)
                resp.raise_for_status()
                data = resp.json()
                
                # Extract the endpoint name from the URL
                endpoint_name = endpoint.split('/')[-2]
                all_data[endpoint_name] = data
                
            except Exception as e:
                endpoint_name = endpoint.split('/')[-2]
                all_data[endpoint_name] = f"Error fetching {endpoint_name} data: {str(e)}"
        
        # Format the response in a readable way
        if all_data:
            return json.dumps(all_data, indent=2, ensure_ascii=False)
        else:
            return "No data available for this user"
            
    except Exception as e:
        return f"Error getting financial information: {e}"

if __name__ == "__main__":
    mcp.run(transport="streamable-http")