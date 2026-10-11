from fastmcp import FastMCP

from database.postgres import initialize_database

from tools.auth_tools import register_auth_tools
from tools.salesperson_tools import register_salesperson_tools
from tools.manager_tools import register_manager_tools
from resources.bill_resources import register_bill_resources


# Initialize database
initialize_database()
 

# Create MCP server
mcp = FastMCP("RetailOps")



register_auth_tools(mcp)


register_salesperson_tools(mcp)

# Register manager tools
register_manager_tools(mcp)

# Register resources (invoice email template)
register_bill_resources(mcp)


if __name__ == "__main__":
    mcp.run()