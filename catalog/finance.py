"""Atomic inventory sales and a cash-based, 50/50 partner ledger."""

from decimal import Decimal, ROUND_HALF_UP
from datetime import timedelta

from django.db import transaction
from django.db.models import Sum, Q
from django.utils import timezone

from .models import BoardGame, CashEntry, FinanceAccount, PartnerTransfer, Sale, StockReservation

ZERO = Decimal('0.00')


def lock_ledger():
    account, _ = FinanceAccount.objects.get_or_create(name='main')
    return FinanceAccount.objects.select_for_update().get(pk=account.pk)


def ledger_summary():
    totals = CashEntry.objects.aggregate(
        receipts=Sum('amount', filter=Q(kind='receipt')),
        refunds=Sum('amount', filter=Q(kind='refund')),
        partner_receipts=Sum('amount', filter=Q(kind='receipt', holder='partner')),
        partner_refunds=Sum('amount', filter=Q(kind='refund', holder='partner')),
    )
    receipts, refunds = totals['receipts'] or ZERO, totals['refunds'] or ZERO
    net = receipts - refunds
    partner_share = (net / Decimal('2')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    held = (totals['partner_receipts'] or ZERO) - (totals['partner_refunds'] or ZERO)
    transfers = PartnerTransfer.objects.aggregate(
        paid=Sum('amount', filter=Q(direction='to_partner')),
        returned=Sum('amount', filter=Q(direction='from_partner')),
    )
    paid = (transfers['paid'] or ZERO) - (transfers['returned'] or ZERO)
    balance = partner_share - held - paid
    return {
        'receipts': receipts, 'refunds': refunds, 'net_received': net,
        'partner_share': partner_share, 'business_share': net - partner_share,
        'partner_held': held, 'partner_transferred': paid, 'partner_balance': balance,
        'owed_to_partner': max(balance, ZERO), 'owed_by_partner': max(-balance, ZERO),
    }


@transaction.atomic
def record_sale(*, game, quantity, unit_price, customer_name, reference, sale_date,
                deduct_stock, request_id, actor=None, reservation=None):
    lock_ledger()
    existing = Sale.objects.filter(request_id=request_id).first()
    if existing:
        return existing
    game = BoardGame.objects.select_for_update().get(pk=game.pk)
    if deduct_stock:
        if game.is_sold or quantity > game.available_quantity:
            raise ValueError('Not enough unreserved stock. For a historical sale, clear "Deduct from current stock".')
        game.stock_quantity -= quantity
        game.is_sold = game.stock_quantity == 0
        game.save()
    sale = Sale(game=game, game_name=game.name, quantity=quantity, unit_price=unit_price,
                customer_name=customer_name, reference=reference, sale_date=sale_date,
                stock_deducted=deduct_stock, request_id=request_id, recorded_by=actor,
                reservation=reservation)
    sale.full_clean()
    sale.save()
    return sale


@transaction.atomic
def confirm_reserved_sale(reservation_id, actor=None):
    lock_ledger()
    games, reservations = lock_reservation_group(reservation_id)
    if any(r.status != 'active' or r.expires_at <= timezone.now() for r in reservations):
        raise ValueError('Only active, unexpired reservations can be confirmed.')
    needed = {}
    for reservation in reservations:
        needed[reservation.game_id] = needed.get(reservation.game_id, 0) + reservation.quantity
    for game_id, quantity in needed.items():
        if games[game_id].is_sold or games[game_id].stock_quantity < quantity:
            raise ValueError('Insufficient stock to confirm this reservation bundle.')
    sales = {}
    for reservation in reservations:
        game = games[reservation.game_id]
        unit_price = reservation.quoted_unit_price if reservation.quoted_unit_price is not None else game.final_price
        if unit_price is None:
            raise ValueError('Set a selling price before confirming the sale.')
        sale = Sale.objects.create(
            game=game, game_name=game.name, quantity=reservation.quantity, unit_price=unit_price,
            customer_name=reservation.customer_name, reference=f'Reservation #{reservation.pk}',
            reservation=reservation, recorded_by=actor,
        )
        sales[reservation.pk] = sale
        reservation.status = 'confirmed'
        reservation.confirmed_at = timezone.now()
        reservation.save()
    for game_id, quantity in needed.items():
        game = games[game_id]
        game.stock_quantity -= quantity
        game.is_sold = game.stock_quantity == 0
        game.save()
    return sales[reservation_id]


def lock_reservation_group(reservation_id):
    """Caller holds the ledger lock; bundle actions always affect the whole quote."""
    initial = StockReservation.objects.get(pk=reservation_id)
    related = StockReservation.objects.filter(quote_group=initial.quote_group) if initial.quote_group else StockReservation.objects.filter(pk=reservation_id)
    games = {game.pk: game for game in BoardGame.objects.select_for_update().filter(
        pk__in=related.values('game_id')).order_by('pk')}
    reservations = list(related.select_for_update().order_by('pk'))
    return games, reservations


@transaction.atomic
def update_reservation(reservation_id, *, cancel=False, minutes=30):
    lock_ledger()
    games, reservations = lock_reservation_group(reservation_id)
    if any(r.status != 'active' for r in reservations):
        raise ValueError('Only active reservations can be cancelled or extended.')
    now = timezone.now()
    if not cancel and (any(r.expires_at <= now for r in reservations) or not 1 <= minutes <= 1440):
        raise ValueError('Only unexpired reservations can be extended, by 1 to 1440 minutes.')
    for reservation in reservations:
        if cancel:
            reservation.status = 'cancelled'
            reservation.cancelled_at = now
        else:
            reservation.expires_at = now + timedelta(minutes=minutes)
        reservation.save()


@transaction.atomic
def record_cash(*, sale, kind, holder, amount, date, method, reference, notes, request_id, actor=None):
    lock_ledger()
    existing = CashEntry.objects.filter(request_id=request_id).first()
    if existing:
        return existing
    sale = Sale.objects.select_for_update().get(pk=sale.pk)
    if date < sale.sale_date:
        raise ValueError('The payment or refund date cannot be before the sale date.')
    if kind == 'receipt' and amount > sale.outstanding:
        raise ValueError(f'The payment exceeds the outstanding balance of €{sale.outstanding:.2f}.')
    if kind == 'refund' and amount > sale.received:
        raise ValueError('A refund cannot exceed the net payments received for this sale.')
    entry = CashEntry(sale=sale, kind=kind, holder=holder, amount=amount, date=date,
                      method=method, reference=reference, notes=notes, request_id=request_id, recorded_by=actor)
    entry.full_clean()
    entry.save()
    return entry


@transaction.atomic
def record_transfer(*, direction, amount, date, reference, notes, request_id, actor=None):
    lock_ledger()
    existing = PartnerTransfer.objects.filter(request_id=request_id).first()
    if existing:
        return existing
    summary = ledger_summary()
    allowed = summary['owed_to_partner'] if direction == 'to_partner' else summary['owed_by_partner']
    if amount > allowed:
        raise ValueError(f'The transfer exceeds the current reconciliation balance of €{allowed:.2f}.')
    entry = PartnerTransfer(direction=direction, amount=amount, date=date, reference=reference,
                            notes=notes, request_id=request_id, recorded_by=actor)
    entry.full_clean()
    entry.save()
    return entry
