from database.postgres import (
    close_billing_request,
    get_billing_request,
    get_customer_by_mobile,
    get_sale_bill,
    list_billing_requests,
)
from services import cart_service
from services.billing_service import generate_bill
from services.escalation_service import escalate_cart
from services.loyalty_service import get_loyalty_discount_percent
from services.offer_service import calculate_offer_discount
from services.product_service import get_product_by_id, search_product_by_name
from tools.auth_tools import require_role


def staff_only(session_id):
    """Salespersons and managers may use these tools."""
    return require_role(session_id, "salesperson", "manager")


def register_salesperson_tools(mcp):

    @mcp.tool()
    def search_product(session_id: str, name: str):
        """Search products by name (shows selling price and stock)."""
        staff_only(session_id)
        return search_product_by_name(name)

    @mcp.tool()
    def check_product_price(session_id: str, product_id: int):
        """Get the price and stock of one product."""
        staff_only(session_id)
        product = get_product_by_id(product_id)
        if not product:
            return {"success": False, "message": "Product not found"}
        return {
            "success": True,
            "product_id": product["id"],
            "name": product["name"],
            "selling_price": float(product["selling_price"]),
            "stock": product["quantity"],
        }

    @mcp.tool()
    def create_cart(session_id: str, cart_id: str):
        """Create an empty cart (or open it if it already exists)."""
        staff_only(session_id)
        return cart_service.create_cart(cart_id)

    @mcp.tool()
    def add_item_to_cart(session_id: str, cart_id: str, product_id: int, quantity: int):
        """Add a product to a cart."""
        staff_only(session_id)
        return cart_service.add_to_cart(cart_id, product_id, quantity)

    @mcp.tool()
    def view_cart(session_id: str, cart_id: str):
        """Show the items and subtotal of a cart."""
        staff_only(session_id)
        return cart_service.get_cart(cart_id) or {"success": False, "message": "Cart not found"}

    @mcp.tool()
    def remove_cart_item(session_id: str, cart_id: str, product_id: int):
        """Remove a product from a cart."""
        staff_only(session_id)
        return cart_service.remove_from_cart(cart_id, product_id)

    @mcp.tool()
    def clear_customer_cart(session_id: str, cart_id: str):
        """Empty and delete a cart."""
        staff_only(session_id)
        return cart_service.clear_cart(cart_id)

    @mcp.tool()
    def check_customer_loyalty(session_id: str, mobile: str):
        """Look up a customer by mobile number and see their loyalty discount."""
        staff_only(session_id)
        customer = get_customer_by_mobile(mobile)
        if not customer:
            return {"found": False, "message": "Customer not found"}
        return {
            "found": True,
            "customer_name": customer["name"],
            "mobile": customer["mobile"],
            "lifetime_profit": float(customer["lifetime_profit"]),
            "loyalty_points": customer["loyalty_points"],
            "loyalty_discount": get_loyalty_discount_percent(customer["lifetime_profit"]),
        }

    @mcp.tool()
    def check_offer(session_id: str, cart_id: str, offer_code: str):
        """Check how much discount an offer code gives on a cart."""
        staff_only(session_id)
        cart = cart_service.get_cart(cart_id)
        if not cart:
            return {"success": False, "message": "Cart not found"}
        try:
            discount = calculate_offer_discount(offer_code, cart["subtotal"])
        except ValueError as error:
            return {"success": False, "message": str(error)}
        return {"success": True, "offer_code": offer_code.upper(), "discount": discount}

    @mcp.tool()
    def generate_customer_bill(
        session_id: str,
        cart_id: str,
        customer_name: str,
        mobile: str,
        email: str,
        offer_code: str | None = None,
    ):
        """Generate the final bill for a cart yourself (customer name, mobile and email are required)."""
        user = staff_only(session_id)
        bill = generate_bill(
            cart_id=cart_id,
            customer_name=customer_name,
            mobile=mobile,
            email=email,
            offer_code=offer_code,
            salesperson_id=user["user_id"],
        )
        # If this cart was already waiting at the billing counter, that request is now done.
        close_billing_request(cart_id, "BILLED", user["user_id"], bill["sale_id"])
        return bill

    @mcp.tool()
    def escalate_cart_to_billing(
        session_id: str,
        cart_id: str,
        customer_name: str | None = None,
        mobile: str | None = None,
        email: str | None = None,
        offer_code: str | None = None,
        note: str | None = None,
    ):
        """
        Send a cart to the billing counter so the cashier can collect payment and
        generate the bill. Use this when the customer is ready to pay and the bill
        should be finished at the counter. Customer details, an offer code and a note
        are optional - the cashier can fill in anything that is missing.
        """
        user = staff_only(session_id)
        try:
            request = escalate_cart(
                cart_id, user["user_id"], customer_name, mobile, email, offer_code, note
            )
        except ValueError as error:
            return {"success": False, "message": str(error)}
        return {
            "success": True,
            "request_id": request["id"],
            "status": request["status"],
            "message": f"Cart {cart_id} sent to the billing counter (request #{request['id']}).",
        }

    @mcp.tool()
    def billing_request_status(session_id: str, request_id: int | None = None):
        """
        Check carts sent to the billing counter. Give a request_id to see one request
        (it includes the final bill once the counter has billed it), or leave it empty
        to list the latest requests (managers see everyone's, salespersons see their own).
        """
        user = staff_only(session_id)
        is_manager = user["role"].upper() == "MANAGER"

        if request_id is None:
            return list_billing_requests(
                requested_by=None if is_manager else user["user_id"], limit=10
            )

        request = get_billing_request(request_id)
        if not request or (not is_manager and request["requested_by"] != user["user_id"]):
            return {"success": False, "message": "Request not found"}
        if request["sale_id"]:
            request["bill"] = get_sale_bill(request["sale_id"])
        return request
