"""Evaluate quantity offers with exact cents and immutable per-unit quote prices."""
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Q
from django.utils import timezone

from .models import Promotion

ZERO = Decimal('0.00')
CENT = Decimal('0.01')


def active_cart_offers():
    now = timezone.now()
    return Promotion.objects.filter(
        is_active=True, kind__in=Promotion.CART_KINDS, starts_at__lte=now,
    ).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now)).prefetch_related('games').order_by('id')


def allocate_discount(prices, indices, discount):
    """Allocate a fixed basket discount proportionally, with largest-remainder cents."""
    subtotal = sum((prices[index] for index in indices), ZERO)
    discount = min(discount, subtotal)
    if not subtotal or not discount:
        return
    cents = int(discount * 100)
    weights = [(index, Decimal(cents) * prices[index] / subtotal) for index in indices]
    allocated = {index: int(weight) for index, weight in weights}
    remaining = cents - sum(allocated.values())
    for index, weight in sorted(weights, key=lambda pair: (-(pair[1] % 1), pair[0]))[:remaining]:
        allocated[index] += 1
    for index, amount in allocated.items():
        prices[index] -= Decimal(amount) * CENT


def price_cart(cart, games):
    """Choose between existing per-item prices and each independent basket offer.

    Quantities count physical copies, including multiple copies of one game.
    Conditional offers use base selling prices, never MSRP or stacked discounts.
    """
    lines, units, base_prices, item_prices = [], [], [], []
    valid = True
    for game_id, quantity in sorted(cart.items(), key=lambda entry: int(entry[0])):
        if type(quantity) is not int or not 1 <= quantity <= 10000:
            raise ValueError('Cart quantities must be whole numbers between 1 and 10000.')
        game = games.get(int(game_id))
        if game is None:
            raise ValueError('A game in this cart no longer exists. Please remove it and try again.')
        start = len(units)
        known = game.base_price is not None
        valid = valid and known and not game.is_sold and quantity <= game.available_quantity
        for _ in range(quantity):
            units.append(game)
            base_prices.append(game.base_price if known else ZERO)
            item_prices.append(game.final_price if known else ZERO)
        lines.append({'game': game, 'quantity': quantity, 'indices': list(range(start, len(units))),
                      'price_known': known})

    chosen = item_prices
    total = sum(chosen, ZERO)
    applied = None
    offers = []
    for offer in active_cart_offers():
        eligible_ids = {game.pk for game in offer.games.all()}
        indices = [index for index, game in enumerate(units)
                   if game.base_price is not None and not game.is_sold
                   and (offer.apply_to_all or game.pk in eligible_ids)]
        missing = max(0, offer.minimum_quantity - len(indices))
        offers.append({'promotion': offer, 'missing': missing, 'qualified': not missing})
        if missing:
            continue
        candidate = list(base_prices)
        if offer.kind == 'cart_percentage':
            for index in indices:
                candidate[index] = (candidate[index] * (1 - offer.value / 100)).quantize(CENT, rounding=ROUND_HALF_UP)
        elif offer.kind == 'cart_amount':
            allocate_discount(candidate, indices, offer.value)
        elif offer.repeat_free_groups:
            # Best complete groups for the customer: highest values grouped first.
            ordered = sorted(indices, key=lambda index: (-candidate[index], index))
            for offset in range(offer.minimum_quantity - 1, len(ordered), offer.minimum_quantity):
                candidate[ordered[offset]] = ZERO
        else:
            candidate[min(indices, key=lambda index: (candidate[index], index))] = ZERO
        candidate_total = sum(candidate, ZERO)
        if candidate_total < total:
            chosen, total, applied = candidate, candidate_total, offer

    for line in lines:
        indices = line.pop('indices')
        line['original_total'] = sum((base_prices[index] for index in indices), ZERO)
        line['item_total'] = sum((chosen[index] for index in indices), ZERO)
        line['discount'] = line['original_total'] - line['item_total']
        line['price_groups'] = sorted(Counter(chosen[index] for index in indices).items(), reverse=True)
    subtotal = sum(base_prices, ZERO)
    return {'cart_items': lines, 'subtotal': subtotal, 'total': total,
            'discount': subtotal - total, 'applied_promotion': applied, 'cart_offers': offers,
            'can_checkout': bool(lines) and valid}
