from database.mongodb import carts

from database.postgres import (
    get_customer_by_mobile,
    create_customer,
    get_product,
    create_sale,
    create_sale_items,
    update_customer_profit,
    decrease_product_stock
)

from services.cart_service import (
    get_cart
)

from services.loyalty_service import (
    get_loyalty_discount_percent
)

from services.offer_service import (
    calculate_offer_discount
)

from services.pricing_service import (
    apply_discount,
    maximum_discount
)


def generate_bill(
    cart_id,
    customer_name,
    mobile,
    email,
    offer_code=None
):

    # -------------------------------
    # Validation
    # -------------------------------

    if not customer_name:
        raise ValueError(
            "Customer name is required"
        )

    if not mobile:
        raise ValueError(
            "Mobile number is required"
        )

    if not email:
        raise ValueError(
            "Email is required"
        )

    cart = get_cart(cart_id)

    if not cart or not cart["items"]:
        raise ValueError(
            "Cart is empty"
        )

    # -------------------------------
    # Customer
    # -------------------------------

    customer = get_customer_by_mobile(
        mobile
    )

    if not customer:

        customer = create_customer(
            customer_name,
            mobile,
            email
        )

    customer_id = customer["id"]

    lifetime_profit = float(
        customer["lifetime_profit"]
    )

    # -------------------------------
    # Prepare items
    # -------------------------------

    items = []

    subtotal = 0

    for cart_item in cart["items"]:

        product = get_product(
            cart_item["product_id"]
        )

        if not product:
            raise ValueError(
                f"Product "
                f"{cart_item['product_id']} "
                f"not found"
            )

        if product["quantity"] < cart_item["quantity"]:
            raise ValueError(
                f"Insufficient stock for "
                f"{product['name']}"
            )

        items.append({
            "product_id":
                product["id"],

            "name":
                product["name"],

            "quantity":
                cart_item["quantity"],

            "cost_price":
                float(product["cost_price"]),

            "selling_price":
                float(product["selling_price"])
        })

        subtotal += (
            float(product["selling_price"])
            * cart_item["quantity"]
        )

    # -------------------------------
    # Calculate offer
    # -------------------------------

    offer_discount = 0

    if offer_code:

        offer_discount = (
            calculate_offer_discount(
                offer_code,
                subtotal
            )
        )

    # -------------------------------
    # Calculate loyalty
    # -------------------------------

    loyalty_percent = (
        get_loyalty_discount_percent(
            lifetime_profit
        )
    )

    loyalty_discount = (
        subtotal
        * loyalty_percent
        / 100
    )

    # ---------------------------------
    # Choose ONE discount
    # ---------------------------------

    if offer_discount >= loyalty_discount:

        requested_discount = (
            offer_discount
        )

        discount_type = "OFFER"

    else:

        requested_discount = (
            loyalty_discount
        )

        discount_type = "LOYALTY"

    # ---------------------------------
    # Apply discount item-by-item
    # ---------------------------------

    total_discount = 0

    total_profit = 0

    final_amount = 0

    sale_items = []

    for item in items:

        item_subtotal = (
            item["selling_price"]
            * item["quantity"]
        )

        # Proportional discount
        if subtotal > 0:

            item_discount = (
                requested_discount
                * item_subtotal
                / subtotal
            )

        else:

            item_discount = 0

        requested_item_discount = (
            item_discount
            / item["quantity"]
        )

        result = apply_discount(
            item["cost_price"],
            item["selling_price"],
            requested_item_discount
        )

        actual_discount = (
            result["discount"]
        )

        final_unit_price = (
            result["final_price"]
        )

        item_profit = (
            result["profit"]
            * item["quantity"]
        )

        item_total = (
            final_unit_price
            * item["quantity"]
        )

        total_discount += (
            actual_discount
            * item["quantity"]
        )

        final_amount += item_total

        total_profit += item_profit

        sale_items.append({
            "product_id":
                item["product_id"],

            "product_name":
                item["name"],

            "quantity":
                item["quantity"],

            "cost_price":
                item["cost_price"],

            "selling_price":
                item["selling_price"],

            "discount":
                actual_discount,

            "final_unit_price":
                final_unit_price,

            "total_price":
                item_total,

            "profit":
                item_profit
        })

    # ---------------------------------
    # Create sale
    # ---------------------------------

    sale = create_sale({
        "customer_id":
            customer_id,

        "subtotal":
            subtotal,

        "discount_type":
            discount_type,

        "offer_discount":
            total_discount
            if discount_type == "OFFER"
            else 0,

        "loyalty_discount":
            total_discount
            if discount_type == "LOYALTY"
            else 0,

        "final_amount":
            final_amount,

        "total_profit":
            total_profit
    })

    # ---------------------------------
    # Add sale items
    # ---------------------------------

    for item in sale_items:

        item["sale_id"] = sale["id"]

    create_sale_items(
        sale_items
    )

    # ---------------------------------
    # Reduce stock
    # ---------------------------------

    for item in sale_items:

        decrease_product_stock(
            item["product_id"],
            item["quantity"]
        )

    # ---------------------------------
    # Loyalty points
    # ---------------------------------

    loyalty_points = int(
        final_amount // 100
    )

    update_customer_profit(
        customer_id,
        total_profit,
        loyalty_points
    )

    # ---------------------------------
    # Clear cart
    # ---------------------------------

    carts.delete_one({
        "_id": cart_id
    })

    # ---------------------------------
    # Return bill data
    # ---------------------------------

    return {
        "success": True,

        "sale_id":
            sale["id"],

        "customer_name":
            customer_name,

        "mobile":
            mobile,

        "email":
            email,

        "items":
            sale_items,

        "subtotal":
            subtotal,

        "discount":
            total_discount,

        "discount_type":
            discount_type,

        "final_amount":
            final_amount,

        "profit":
            total_profit,

        "loyalty_points_earned":
            loyalty_points
    }