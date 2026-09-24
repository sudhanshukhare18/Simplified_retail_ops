from config import MINIMUM_PROFIT


def maximum_discount(
    cost_price,
    selling_price
):

    current_profit = (
        selling_price - cost_price
    )

    maximum = (
        current_profit - MINIMUM_PROFIT
    )

    return max(0, maximum)


def apply_discount(
    cost_price,
    selling_price,
    requested_discount
):

    max_discount = maximum_discount(
        cost_price,
        selling_price
    )

    actual_discount = min(
        requested_discount,
        max_discount
    )

    final_price = (
        selling_price - actual_discount
    )

    profit = (
        final_price - cost_price
    )

    return {
        "selling_price": selling_price,
        "discount": actual_discount,
        "final_price": final_price,
        "profit": profit
    }


def calculate_cart_discount(
    cart_items,
    discount_percent
):

    total_discount = 0

    calculated_items = []

    for item in cart_items:

        cost_price = item["cost_price"]

        selling_price = item["selling_price"]

        quantity = item["quantity"]

        requested_discount = (
            selling_price
            * discount_percent
            / 100
        )

        result = apply_discount(
            cost_price,
            selling_price,
            requested_discount
        )

        result["product_id"] = (
            item["product_id"]
        )

        result["name"] = item["name"]

        result["quantity"] = quantity

        total_discount += (
            result["discount"]
            * quantity
        )

        calculated_items.append(result)

    return {
        "discount": total_discount,
        "items": calculated_items
    }