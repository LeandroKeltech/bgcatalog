def round_to_nearest_5(value):
    """
    Round to nearest multiple of 5.
    Ties (x.5) round down.
    """
    if value % 5 == 2.5:
        return int(value - 2.5)
    return round(value / 5) * 5

def calculate_suggested_price(reference_price, rule_percent=-50):
    """
    Calculate suggested price from reference price and rule percentage.
    Apply rounding to nearest 5.
    """
    suggested = reference_price * (1 + rule_percent / 100)
    return round_to_nearest_5(suggested)
