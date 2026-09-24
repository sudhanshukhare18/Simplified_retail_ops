from fastmcp import FastMCP

from database.postgres import initialize_database

from tools.auth_tools import register_auth_tools
from tools.salesperson_tools import register_salesperson_tools
from tools.manager_tools import register_manager_tools


# Initialize database
initialize_database()


# Create MCP server
mcp = FastMCP("RetailOps")


# Register authentication
register_auth_tools(mcp)

# Register salesperson tools
register_salesperson_tools(mcp)

# Register manager tools
register_manager_tools(mcp)


if __name__ == "__main__":
    mcp.run()