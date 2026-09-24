from datetime import datetime

from database.postgres import (
    get_offer
)


def calculate_offer_discount(
    code,
    subtotal
):

    offer = get_offer(code)

    if not offer:
        raise ValueError(
            "Invalid offer code"
        )

    if offer["expires_at"]:

        expiry = (
            datetime.fromisoformat(
                offer["expires_at"]
                .replace("Z", "+00:00")
            )
        )

        if expiry < datetime.now(
            expiry.tzinfo
        ):
            raise ValueError(
                "Offer has expired"
            )

    if subtotal < float(
        offer["minimum_amount"]
    ):
        raise ValueError(
            f"Minimum purchase amount is "
            f"₹{offer['minimum_amount']}"
        )

    if offer["discount_type"] == "PERCENTAGE":

        discount = (
            subtotal
            * float(offer["discount_value"])
            / 100
        )

    else:

        discount = float(
            offer["discount_value"]
        )

    if offer["maximum_discount"]:

        discount = min(
            discount,
            float(offer["maximum_discount"])
        )

    return discount