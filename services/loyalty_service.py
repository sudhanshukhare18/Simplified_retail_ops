from config import (
    LOYALTY_PROFIT_THRESHOLD,
    LOYALTY_DISCOUNT_PERCENT
)


def is_loyal_customer(
    lifetime_profit
):

    return (
        float(lifetime_profit)
        > LOYALTY_PROFIT_THRESHOLD
    )


def get_loyalty_discount_percent(
    lifetime_profit
):

    if is_loyal_customer(
        lifetime_profit
    ):
        return LOYALTY_DISCOUNT_PERCENT

    return 0