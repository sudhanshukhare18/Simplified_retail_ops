from database.postgres import (
    create_offer,
    create_product,
    deactivate_product,
    decrease_product_stock,
    disable_offer,
    get_monthly_sales,
    get_sales_by_time,
    increase_product_stock,
    list_offers,
)
from tools.auth_tools import require_role


def manager_only(session_id):
    return require_role(session_id, "manager")


def register_manager_tools(mcp):

    @mcp.tool()
    def manager_add_product(
        session_id: str,
        name: str,
        category: str,
        cost_price: float,
        selling_price: float,
        quantity: int,
    ):
        """Add a new product to the shop."""
        manager_only(session_id)
        if selling_price < cost_price:
            return {"success": False, "message": "Selling price cannot be below cost price."}
        product = create_product(name, category, cost_price, selling_price, quantity)
        return {"success": True, "product": product}

    @mcp.tool()
    def manager_delete_product(session_id: str, product_id: int):
        """Remove a product from sale."""
        manager_only(session_id)
        product = deactivate_product(product_id)
        if not product:
            return {"success": False, "message": "Product not found"}
        return {"success": True, "message": "Product deleted", "product": product}

    @mcp.tool()
    def manager_increase_stock(session_id: str, product_id: int, quantity: int):
        """Add units to a product's stock."""
        manager_only(session_id)
        if quantity <= 0:
            return {"success": False, "message": "Quantity must be greater than 0"}
        product = increase_product_stock(product_id, quantity)
        if not product:
            return {"success": False, "message": "Product not found"}
        return {"success": True, "product": product}

    @mcp.tool()
    def manager_decrease_stock(session_id: str, product_id: int, quantity: int):
        """Remove units from a product's stock."""
        manager_only(session_id)
        if quantity <= 0:
            return {"success": False, "message": "Quantity must be greater than 0"}
        product = decrease_product_stock(product_id, quantity)
        if not product:
            return {"success": False, "message": "Insufficient stock or product not found"}
        return {"success": True, "product": product}

    @mcp.tool()
    def manager_monthly_sales(session_id: str, month: int | None = None, year: int | None = None):
        """Orders, revenue and profit for a month (defaults to the current month)."""
        manager_only(session_id)
        return get_monthly_sales(month, year)

    @mcp.tool()
    def manager_sales_by_time(session_id: str, start_time: str, end_time: str):
        """Sales between two date-times (ISO format, e.g. 2026-10-01T00:00:00+05:30)."""
        manager_only(session_id)
        return get_sales_by_time(start_time, end_time)

    @mcp.tool()
    def manager_create_offer(
        session_id: str,
        code: str,
        discount_type: str,
        discount_value: float,
        minimum_amount: float = 0,
        maximum_discount: float | None = None,
        expires_at: str | None = None,
    ):
        """Create an offer code. discount_type is PERCENTAGE or FLAT."""
        manager_only(session_id)
        if discount_type.upper() not in ("PERCENTAGE", "FLAT"):
            return {"success": False, "message": "discount_type must be PERCENTAGE or FLAT"}
        return create_offer(
            code, discount_type, discount_value, minimum_amount, maximum_discount, expires_at
        )

    @mcp.tool()
    def manager_disable_offer(session_id: str, code: str):
        """Turn an offer code off."""
        manager_only(session_id)
        return disable_offer(code)

    @mcp.tool()
    def manager_list_offers(session_id: str):
        """List the active offers."""
        manager_only(session_id)
        return list_offers()
