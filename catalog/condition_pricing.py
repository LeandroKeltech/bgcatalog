"""Condition-based base prices, independent of scheduled promotions."""
from decimal import Decimal, ROUND_HALF_UP

CONDITION_DISCOUNTS = {
    'new': 30,
    'like_new': 40,
    'used': 60,
    'very_good': 60,
    'good': 60,
    'acceptable': 60,
}


def condition_price(original_price, condition):
    if original_price is None:
        return None
    discount = CONDITION_DISCOUNTS[condition]
    return (original_price * (Decimal('100') - discount) / 100).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP,
    )
