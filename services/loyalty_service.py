from config import LOYALTY_PROFIT_THRESHOLD, LOYALTY_DISCOUNT_PERCENT


def get_loyalty_discount_percent(lifetime_profit):
    """Loyal customers (lifetime profit above the threshold) get a fixed discount, others get 0."""
    if float(lifetime_profit) > LOYALTY_PROFIT_THRESHOLD:
        return LOYALTY_DISCOUNT_PERCENT
    return 0
