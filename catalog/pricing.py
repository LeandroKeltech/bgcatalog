"""Database prices use the same best-offer rules as the model display."""
from decimal import Decimal

from django.db.models import Q, F, Case, When, DecimalField, FloatField, OuterRef, Subquery, Value
from django.db.models.functions import Cast, Coalesce, Greatest, Round
from django.utils import timezone

from .models import Promotion


def with_selling_price(games):
    money = DecimalField(max_digits=10, decimal_places=2)
    games = games.annotate(base_selling_price=Case(
        When(sale_price__isnull=False, then=F('sale_price')),
        default=Round(Cast('msrp_price', FloatField()) * (1.0 - F('discount_percentage') / 100.0), 2),
        output_field=money,
    ))
    now = timezone.now()
    active = Promotion.objects.filter(is_active=True, starts_at__lte=now, kind__in=Promotion.ITEM_KINDS).filter(
        Q(ends_at__isnull=True) | Q(ends_at__gt=now)
    ).filter(Q(apply_to_all=True) | Q(games=OuterRef('pk'))).annotate(
        candidate=Greatest(Value(Decimal('0.00'), output_field=money), Case(
            When(kind='percentage', then=Round(
                Cast(OuterRef('base_selling_price'), FloatField()) * (1.0 - Cast('value', FloatField()) / 100.0), 2)),
            When(kind='amount', then=OuterRef('base_selling_price') - F('value')),
            default=F('value'), output_field=money,
        ), output_field=money)
    ).filter(candidate__lt=OuterRef('base_selling_price')).order_by('candidate', 'id')
    return games.annotate(selling_price=Coalesce(
        Subquery(active.values('candidate')[:1], output_field=money), F('base_selling_price'), output_field=money,
    ))
