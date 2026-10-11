from config import MINIMUM_PROFIT


def apply_discount(cost_price, selling_price, requested_discount):
    """Give the requested discount per unit, but never let profit per unit drop below MINIMUM_PROFIT."""
    max_discount = max(0, selling_price - cost_price - MINIMUM_PROFIT)
    discount = min(requested_discount, max_discount)
    final_price = selling_price - discount
    return {
        "discount": discount,
        "final_price": final_price,
        "profit": final_price - cost_price,
    }
