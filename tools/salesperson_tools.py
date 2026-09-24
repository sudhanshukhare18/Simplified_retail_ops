from services.product_service import (
    search_product_by_name,
    get_product_by_id
)

from services.cart_service import (
    add_to_cart,
    get_cart,
    remove_from_cart,
    clear_cart
)

from services.loyalty_service import (
    get_loyalty_discount_percent
)

from database.postgres import (
    get_customer_by_mobile
)

from services.offer_service import (
    calculate_offer_discount
)

from services.billing_service import (
    generate_bill
)

from tools.auth_tools import require_role


def register_salesperson_tools(mcp):

    @mcp.tool()
    def search_product(
        session_id: str,
        name: str
    ):

        require_role(
            session_id,
            "salesperson",
            "manager"
        )

        return search_product_by_name(name)


    @mcp.tool()
    def check_product_price(
        session_id: str,
        product_id: int
    ):

        require_role(
            session_id,
            "salesperson",
            "manager"
        )

        product = get_product_by_id(product_id)

        if not product:
            return {
                "success": False,
                "message": "Product not found"
            }

        return {
            "success": True,
            "product_id": product["id"],
            "name": product["name"],
            "selling_price": float(
                product["selling_price"]
            ),
            "stock": product["quantity"]
        }


    @mcp.tool()
    def create_cart(
        session_id: str,
        cart_id: str
    ):

        require_role(
            session_id,
            "salesperson",
            "manager"
        )

        return get_cart(cart_id)


    @mcp.tool()
    def add_item_to_cart(
        session_id: str,
        cart_id: str,
        product_id: int,
        quantity: int
    ):

        require_role(
            session_id,
            "salesperson",
            "manager"
        )

        return add_to_cart(
            cart_id,
            product_id,
            quantity
        )


    @mcp.tool()
    def view_cart(
        session_id: str,
        cart_id: str
    ):

        require_role(
            session_id,
            "salesperson",
            "manager"
        )

        return get_cart(cart_id)


    @mcp.tool()
    def remove_cart_item(
        session_id: str,
        cart_id: str,
        product_id: int
    ):

        require_role(
            session_id,
            "salesperson",
            "manager"
        )

        return remove_from_cart(
            cart_id,
            product_id
        )


    @mcp.tool()
    def clear_customer_cart(
        session_id: str,
        cart_id: str
    ):

        require_role(
            session_id,
            "salesperson",
            "manager"
        )

        return clear_cart(cart_id)


    @mcp.tool()
    def check_customer_loyalty(
        session_id: str,
        mobile: str
    ):

        require_role(
            session_id,
            "salesperson",
            "manager"
        )

        customer = get_customer_by_mobile(mobile)

        if not customer:
            return {
                "found": False,
                "message": "Customer not found"
            }

        discount = get_loyalty_discount_percent(
            customer["lifetime_profit"]
        )

        return {
            "found": True,
            "customer_name": customer["name"],
            "mobile": customer["mobile"],
            "lifetime_profit": float(
                customer["lifetime_profit"]
            ),
            "loyalty_points": customer["loyalty_points"],
            "loyalty_discount": discount
        }


    @mcp.tool()
    def check_offer(
        session_id: str,
        cart_id: str,
        offer_code: str
    ):

        require_role(
            session_id,
            "salesperson",
            "manager"
        )

        cart = get_cart(cart_id)

        if not cart:
            return {
                "success": False,
                "message": "Cart not found"
            }

        try:

            discount = calculate_offer_discount(
                offer_code,
                cart["subtotal"]
            )

            return {
                "success": True,
                "offer_code": offer_code.upper(),
                "discount": discount
            }

        except ValueError as error:

            return {
                "success": False,
                "message": str(error)
            }


    @mcp.tool()
    def generate_customer_bill(
        session_id: str,
        cart_id: str,
        customer_name: str,
        mobile: str,
        email: str,
        offer_code: str = None
    ):

        require_role(
            session_id,
            "salesperson",
            "manager"
        )

        return generate_bill(
            cart_id=cart_id,
            customer_name=customer_name,
            mobile=mobile,
            email=email,
            offer_code=offer_code
        )