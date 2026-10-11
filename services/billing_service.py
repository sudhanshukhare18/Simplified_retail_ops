from database.mongodb import carts
from database.postgres import get_customer_by_mobile, create_customer, get_product, record_sale
from services.cart_service import get_cart
from services.loyalty_service import get_loyalty_discount_percent
from services.offer_service import calculate_offer_discount
from services.pricing_service import apply_discount


def generate_bill(cart_id, customer_name, mobile, email, offer_code=None, salesperson_id=None):
    """Turn a cart into a sale: apply the best single discount, save everything, clear the cart."""

    # ---- validate ----
    for label, value in (("Customer name", customer_name), ("Mobile number", mobile), ("Email", email)):
        if not value:
            raise ValueError(f"{label} is required")

    cart = get_cart(cart_id)
    if not cart or not cart["items"]:
        raise ValueError("Cart is empty")

    customer = get_customer_by_mobile(mobile) or create_customer(customer_name, mobile, email)

    
    lines, subtotal = [], 0
    for cart_item in cart["items"]:
        product = get_product(cart_item["product_id"])
        if not product:
            raise ValueError(f"Product {cart_item['product_id']} not found")
        if product["quantity"] < cart_item["quantity"]:
            raise ValueError(f"Insufficient stock for {product['name']}")
        lines.append((product, cart_item["quantity"]))
        subtotal += float(product["selling_price"]) * cart_item["quantity"]

    
    offer_discount = calculate_offer_discount(offer_code, subtotal) if offer_code else 0
    loyalty_discount = subtotal * get_loyalty_discount_percent(customer["lifetime_profit"]) / 100

    if max(offer_discount, loyalty_discount) == 0:
        discount_type, requested_discount = "NONE", 0
    elif offer_discount >= loyalty_discount:
        discount_type, requested_discount = "OFFER", offer_discount
    else:
        discount_type, requested_discount = "LOYALTY", loyalty_discount

   
    sale_items = []
    total_discount = total_profit = final_amount = 0

    for product, quantity in lines:
        cost, price = float(product["cost_price"]), float(product["selling_price"])
        unit_discount = requested_discount * price / subtotal if subtotal else 0
        priced = apply_discount(cost, price, unit_discount)

        line_total = priced["final_price"] * quantity
        line_profit = priced["profit"] * quantity
        total_discount += priced["discount"] * quantity
        final_amount += line_total
        total_profit += line_profit

        sale_items.append({
            "product_id": product["id"],
            "product_name": product["name"],
            "quantity": quantity,
            "cost_price": cost,
            "selling_price": price,
            "discount": priced["discount"],
            "final_unit_price": priced["final_price"],
            "total_price": line_total,
            "profit": line_profit,
        })

    # ---- save (one transaction) and clear the cart ----
    loyalty_points = int(final_amount // 100)

    sale_id = record_sale(
        {
            "customer_id": customer["id"],
            "salesperson_id": salesperson_id,
            "subtotal": subtotal,
            "discount_type": discount_type,
            "offer_discount": total_discount if discount_type == "OFFER" else 0,
            "loyalty_discount": total_discount if discount_type == "LOYALTY" else 0,
            "final_amount": final_amount,
            "total_profit": total_profit,
        },
        sale_items,
        loyalty_points,
    )

    carts.delete_one({"_id": cart_id})

    return {
        "success": True,
        "sale_id": sale_id,
        "customer_name": customer_name,
        "mobile": mobile,
        "email": email,
        "items": sale_items,
        "subtotal": subtotal,
        "discount": total_discount,
        "discount_type": discount_type,
        "final_amount": final_amount,
        "profit": total_profit,
        "loyalty_points_earned": loyalty_points,
    }
