from database.postgres import (
    create_product,
    deactivate_product,
    increase_product_stock,
    decrease_product_stock,
    get_monthly_sales,
    get_sales_by_time,
    create_offer,
    disable_offer,
    list_offers
)

from tools.auth_tools import require_role


def register_manager_tools(mcp):

    @mcp.tool()
    def manager_add_product(
        session_id: str,
        name: str,
        category: str,
        cost_price: float,
        selling_price: float,
        quantity: int
    ):

        require_role(
            session_id,
            "manager"
        )

        if selling_price - cost_price < 0:
            return {
                "success": False,
                "message": "Selling price cannot be below cost price."
            }

        product = create_product(
            name,
            category,
            cost_price,
            selling_price,
            quantity
        )

        return {
            "success": True,
            "product": product
        }


    @mcp.tool()
    def manager_delete_product(
        session_id: str,
        product_id: int
    ):

        require_role(
            session_id,
            "manager"
        )

        product = deactivate_product(product_id)

        if not product:
            return {
                "success": False,
                "message": "Product not found"
            }

        return {
            "success": True,
            "message": "Product deleted",
            "product": product
        }


    @mcp.tool()
    def manager_increase_stock(
        session_id: str,
        product_id: int,
        quantity: int
    ):

        require_role(
            session_id,
            "manager"
        )

        if quantity <= 0:
            return {
                "success": False,
                "message": "Quantity must be greater than 0"
            }

        product = increase_product_stock(
            product_id,
            quantity
        )

        if not product:
            return {
                "success": False,
                "message": "Product not found"
            }

        return {
            "success": True,
            "product": product
        }


    @mcp.tool()
    def manager_decrease_stock(
        session_id: str,
        product_id: int,
        quantity: int
    ):

        require_role(
            session_id,
            "manager"
        )

        if quantity <= 0:
            return {
                "success": False,
                "message": "Quantity must be greater than 0"
            }

        product = decrease_product_stock(
            product_id,
            quantity
        )

        if not product:
            return {
                "success": False,
                "message": "Insufficient stock or product not found"
            }

        return {
            "success": True,
            "product": product
        }


    @mcp.tool()
    def manager_monthly_sales(
        session_id: str
    ):

        require_role(
            session_id,
            "manager"
        )

        return get_monthly_sales()


    @mcp.tool()
    def manager_sales_by_time(
        session_id: str,
        start_time: str,
        end_time: str
    ):

        require_role(
            session_id,
            "manager"
        )

        return get_sales_by_time(
            start_time,
            end_time
        )


    @mcp.tool()
    def manager_create_offer(
        session_id: str,
        code: str,
        discount_type: str,
        discount_value: float,
        minimum_amount: float = 0,
        maximum_discount: float = None,
        expires_at: str = None
    ):

        require_role(
            session_id,
            "manager"
        )

        return create_offer(
            code,
            discount_type,
            discount_value,
            minimum_amount,
            maximum_discount,
            expires_at
        )


    @mcp.tool()
    def manager_disable_offer(
        session_id: str,
        code: str
    ):

        require_role(
            session_id,
            "manager"
        )

        return disable_offer(code)


    @mcp.tool()
    def manager_list_offers(
        session_id: str
    ):

        require_role(
            session_id,
            "manager"
        )

        return list_offers()