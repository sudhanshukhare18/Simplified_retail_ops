from database.postgres import (
    close_billing_request,
    get_billing_request,
    save_billing_request,
)
from services.billing_service import generate_bill
from services.cart_service import get_cart
from services.offer_service import calculate_offer_discount


def escalate_cart(cart_id, requested_by, customer_name=None, mobile=None,
                  email=None, offer_code=None, note=None):
    """Send a cart to the billing counter. The cashier finishes the bill from the dashboard."""
    cart = get_cart(cart_id)
    if not cart or not cart["items"]:
        raise ValueError("Cart is empty or not found")

    if offer_code:
        offer_code = offer_code.strip().upper()
        calculate_offer_discount(offer_code, cart["subtotal"])  # raises ValueError if unusable

    return save_billing_request(
        cart_id,
        requested_by,
        (customer_name or "").strip() or None,
        (mobile or "").strip() or None,
        (email or "").strip() or None,
        offer_code or None,
        (note or "").strip() or None,
    )


def bill_request(request_id, handled_by, customer_name, mobile, email, offer_code=None):
    """Billing counter: turn a pending request into a real sale."""
    request = get_billing_request(request_id)
    if not request or request["status"] != "PENDING":
        raise ValueError("This request is no longer pending")

    # The sale is credited to the salesperson who sent the cart.
    bill = generate_bill(
        request["cart_id"], customer_name, mobile, email, offer_code,
        salesperson_id=request["requested_by"],
    )
    close_billing_request(request["cart_id"], "BILLED", handled_by, bill["sale_id"])
    return bill


def cancel_request(request_id, handled_by):
    request = get_billing_request(request_id)
    if not request or request["status"] != "PENDING":
        raise ValueError("This request is no longer pending")
    close_billing_request(request["cart_id"], "CANCELLED", handled_by)
