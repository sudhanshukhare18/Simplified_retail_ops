from datetime import datetime, timezone

from database.postgres import get_offer


def calculate_offer_discount(code, subtotal):
    """Return the discount an offer gives on this subtotal, or raise ValueError if it can't be used."""
    offer = get_offer(code)

    if not offer:
        raise ValueError("Invalid offer code")

    if offer["expires_at"] and offer["expires_at"] < datetime.now(timezone.utc):
        raise ValueError("Offer has expired")

    if subtotal < float(offer["minimum_amount"]):
        raise ValueError(f"Minimum purchase amount is ₹{offer['minimum_amount']}")

    value = float(offer["discount_value"])
    discount = subtotal * value / 100 if offer["discount_type"] == "PERCENTAGE" else value

    if offer["maximum_discount"]:
        discount = min(discount, float(offer["maximum_discount"]))

    return discount
