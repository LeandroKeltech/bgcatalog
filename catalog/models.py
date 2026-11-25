from django.db import models
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
import uuid


class BoardGame(models.Model):
    """
    Model representing a board game in the catalog.
    Integrates data from BoardGameGeek, Board Game Atlas, and BoardGamePrices.
    """
    
    CONDITION_CHOICES = [
        ('new', 'New'),
        ('like_new', 'Like New'),
        ('very_good', 'Very Good'),
        ('good', 'Good'),
        ('acceptable', 'Acceptable'),
        ('used', 'Used (grade unspecified)'),
    ]
    
    # Basic Information
    name = models.CharField(max_length=255, help_text="Game name")
    bgg_id = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text="BoardGameGeek ID or BGA ID (prefixed with 'bga_')"
    )
    year_published = models.IntegerField(null=True, blank=True, help_text="Year published")
    designer = models.CharField(max_length=255, blank=True, help_text="Game designer(s)")
    description = models.TextField(blank=True, help_text="Game description")
    description_html = models.TextField(blank=True, help_text='Sanitized structured BGG description')
    
    # Images
    image_url = models.URLField(max_length=500, blank=True, help_text="Full-size image URL")
    thumbnail_url = models.URLField(max_length=500, blank=True, help_text="Thumbnail image URL")
    
    # Gameplay Details
    min_players = models.IntegerField(null=True, blank=True, help_text="Minimum number of players")
    max_players = models.IntegerField(null=True, blank=True, help_text="Maximum number of players")
    min_playtime = models.IntegerField(null=True, blank=True, help_text="Minimum playtime (minutes)")
    max_playtime = models.IntegerField(null=True, blank=True, help_text="Maximum playtime (minutes)")
    min_age = models.IntegerField(null=True, blank=True, help_text="Minimum recommended age")
    average_weight = models.FloatField(
        null=True,
        blank=True,
        help_text="BoardGameGeek community complexity rating (1 to 5)",
    )
    
    # Categories and Mechanics
    categories = models.CharField(max_length=500, blank=True, help_text="Comma-separated categories")
    mechanics = models.CharField(max_length=500, blank=True, help_text="Comma-separated mechanics")
    
    # Ratings
    rating_average = models.FloatField(null=True, blank=True, help_text="Average user rating")
    rating_bayes = models.FloatField(null=True, blank=True, help_text="Bayes average rating")
    rank_overall = models.IntegerField(null=True, blank=True, help_text="Overall BGG rank")
    num_ratings = models.IntegerField(null=True, blank=True, help_text="Number of ratings")
    click_count = models.PositiveBigIntegerField(default=0, help_text='Counted public product opens')
    
    # Pricing
    msrp_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="MSRP price in EUR"
    )
    sale_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Explicit sale price in EUR; overrides the calculated discount",
    )
    source_key = models.CharField(max_length=255, unique=True, null=True, blank=True)
    source_metadata = models.JSONField(default=dict, blank=True)
    discount_percentage = models.IntegerField(
        default=0,
        help_text="Discount percentage (0-100)"
    )
    
    # Inventory
    stock_quantity = models.IntegerField(default=1, help_text="Available stock quantity")
    condition = models.CharField(
        max_length=20,
        choices=CONDITION_CHOICES,
        default='new',
        help_text="Game condition"
    )
    is_sold = models.BooleanField(default=False, help_text="Mark as sold")
    sold_date = models.DateTimeField(null=True, blank=True, help_text="Date sold")
    
    # Admin Notes
    notes = models.TextField(blank=True, help_text="Internal admin notes")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(sale_price__isnull=True) | models.Q(sale_price__gte=0),
                name='game_sale_price_nonnegative',
            ),
            models.CheckConstraint(condition=models.Q(stock_quantity__gte=0), name='game_stock_nonnegative'),
            models.CheckConstraint(
                condition=models.Q(discount_percentage__gte=0, discount_percentage__lte=100),
                name='game_discount_valid',
            ),
            models.CheckConstraint(
                condition=models.Q(msrp_price__isnull=True) | models.Q(msrp_price__gte=0),
                name='game_price_nonnegative',
            ),
        ]
        indexes = [
            models.Index(fields=['bgg_id']),
            models.Index(fields=['name']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_sold']),
            models.Index(fields=['-click_count', '-rating_average', 'id'], name='game_relevance_idx'),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.year_published or 'N/A'})"
    
    @property
    def base_price(self):
        """Selling price before scheduled promotions."""
        if self.sale_price is not None:
            return self.sale_price
        if self.msrp_price is not None:
            discount_multiplier = Decimal('1') - Decimal(self.discount_percentage) / Decimal('100')
            return (self.msrp_price * discount_multiplier).quantize(
                Decimal('0.01'), rounding=ROUND_HALF_UP
            )
        return None

    @cached_property
    def price_info(self):
        base = self.base_price
        result = {'price': base, 'promotion': None, 'saving': Decimal('0.00')}
        if base is None or not self.pk:
            return result
        now = timezone.now()
        candidates = Promotion.objects.filter(is_active=True, starts_at__lte=now, kind__in=Promotion.ITEM_KINDS).filter(
            models.Q(ends_at__isnull=True) | models.Q(ends_at__gt=now)
        ).filter(models.Q(apply_to_all=True) | models.Q(games=self)).distinct().order_by('id')
        for promotion in candidates:
            candidate = promotion.price_for(base)
            if candidate < result['price']:
                result = {'price': candidate, 'promotion': promotion, 'saving': base - candidate}
        return result

    @property
    def final_price(self):
        return self.price_info['price']
    
    @property
    def savings(self):
        """Return real savings against the original price, if any."""
        price = self.final_price
        if self.msrp_price is not None and price is not None and self.msrp_price > price:
            return self.msrp_price - price
        return None

    @property
    def effective_discount_percentage(self):
        price = self.final_price
        if self.msrp_price is None or self.msrp_price <= 0 or price is None or price > self.msrp_price:
            return None
        return ((self.msrp_price - price) / self.msrp_price * 100).quantize(
            Decimal('0.1'), rounding=ROUND_HALF_UP,
        )

    @property
    def formatted_description(self):
        from .content import sanitize_description
        from django.utils.safestring import mark_safe
        return mark_safe(sanitize_description(self.description_html or self.description))

    @property
    def available_quantity(self):
        """Calculate available quantity minus active reservations."""
        reserved = self.reservations.filter(
            status='active',
            expires_at__gt=timezone.now()
        ).aggregate(total=models.Sum('quantity'))['total'] or 0
        return max(0, self.stock_quantity - reserved)
    
    @property
    def reserved_quantity(self):
        """Get total reserved quantity."""
        return self.reservations.filter(
            status='active',
            expires_at__gt=timezone.now()
        ).aggregate(total=models.Sum('quantity'))['total'] or 0
    
    @property
    def players_display(self):
        """Return formatted player count."""
        if self.min_players and self.max_players:
            if self.min_players == self.max_players:
                return f"{self.min_players}"
            return f"{self.min_players}-{self.max_players}"
        elif self.min_players:
            return f"{self.min_players}+"
        return "N/A"
    
    @property
    def playtime_display(self):
        """Return formatted playtime."""
        if self.min_playtime and self.max_playtime:
            if self.min_playtime == self.max_playtime:
                return f"{self.min_playtime} min"
            return f"{self.min_playtime}-{self.max_playtime} min"
        elif self.min_playtime:
            return f"{self.min_playtime}+ min"
        return "N/A"
    
    def save(self, *args, **kwargs):
        """Override save to update sold_date."""
        self.__dict__.pop('price_info', None)
        if self.is_sold and not self.sold_date:
            self.sold_date = timezone.now()
        elif not self.is_sold:
            self.sold_date = None
        super().save(*args, **kwargs)


class SecurityRateLimit(models.Model):
    key = models.CharField(max_length=64, primary_key=True)
    attempts = models.PositiveIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)


class CustomerProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='customer_profile')
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=16)


class CustomerQuote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='customer_quotes')
    snapshot = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']

    @property
    def is_active(self):
        reservations = list(self.reservations.all())
        return bool(reservations) and all(r.status == 'active' and r.expires_at > timezone.now() for r in reservations)

    @property
    def status(self):
        reservations = list(self.reservations.all())
        statuses = {r.status for r in reservations}
        if statuses == {'confirmed'}:
            return 'Confirmed'
        if statuses == {'cancelled'}:
            return 'Cancelled'
        if statuses == {'active'}:
            return 'Reserved' if self.is_active else 'Expired'
        return 'Partially processed' if reservations else 'Unavailable'

    @property
    def reservation_expires_at(self):
        return min((r.expires_at for r in self.reservations.all()), default=self.expires_at)


class AdminReservationNotification(models.Model):
    """One durable alert per checkout; acknowledgement is separate for each admin."""
    quote = models.OneToOneField(CustomerQuote, on_delete=models.PROTECT, related_name='admin_notification')
    created_at = models.DateTimeField(auto_now_add=True)
    read_by = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='read_reservation_notifications')
    email_recipient = models.EmailField(blank=True)
    email_status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pending'), ('sending', 'Sending'), ('sent', 'Sent'),
        ('failed', 'Failed — retry available'), ('not_configured', 'Email setup required'),
    ])
    email_attempted_at = models.DateTimeField(null=True, blank=True)
    email_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-id']


class StockReservation(models.Model):
    """
    Model for managing temporary stock reservations during checkout.
    Prevents overselling by holding stock for 24 hours.
    """
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    # Reservation Details
    game = models.ForeignKey(
        BoardGame,
        on_delete=models.PROTECT,
        related_name='reservations',
        help_text="Reserved game"
    )
    quantity = models.IntegerField(default=1, help_text="Reserved quantity")
    quoted_unit_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quote_group = models.UUIDField(null=True, blank=True, db_index=True)
    promotion_snapshot = models.JSONField(default=dict, blank=True)
    customer_quote = models.ForeignKey(CustomerQuote, null=True, blank=True, on_delete=models.PROTECT, related_name='reservations')
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='active',
        help_text="Reservation status"
    )
    
    # Customer Information
    customer_name = models.CharField(max_length=255, help_text="Customer name")
    customer_email = models.EmailField(help_text="Customer email")
    customer_phone = models.CharField(max_length=50, blank=True, help_text="Customer phone")
    
    # Session Tracking
    session_key = models.CharField(max_length=255, help_text="Session key")
    
    # Timestamps
    reserved_at = models.DateTimeField(auto_now_add=True, help_text="Reservation created")
    expires_at = models.DateTimeField(help_text="Reservation expires")
    confirmed_at = models.DateTimeField(null=True, blank=True, help_text="Sale confirmed")
    cancelled_at = models.DateTimeField(null=True, blank=True, help_text="Reservation cancelled")
    
    # Admin Notes
    admin_notes = models.TextField(blank=True, help_text="Admin notes")
    
    class Meta:
        ordering = ['-reserved_at']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quoted_unit_price__isnull=True) | models.Q(quoted_unit_price__gte=0),
                name='reservation_quote_nonnegative',
            ),
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name='reservation_quantity_positive'),
            models.CheckConstraint(
                condition=models.Q(status__in=['active', 'confirmed', 'cancelled', 'expired']),
                name='reservation_status_valid',
            ),
        ]
        indexes = [
            models.Index(fields=['status', 'expires_at']),
            models.Index(fields=['session_key']),
            models.Index(fields=['game', 'status']),
        ]
    
    def __str__(self):
        return f"{self.game.name} - {self.quantity}x ({self.status})"
    
    def save(self, *args, **kwargs):
        """Set expiry time on creation."""
        if not self.pk and not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if reservation has expired."""
        return timezone.now() > self.expires_at and self.status == 'active'

    @property
    def bundle_reservations(self):
        if not self.quote_group:
            return StockReservation.objects.none()
        return StockReservation.objects.filter(quote_group=self.quote_group).select_related('game').order_by('id')
    
    @property
    def time_remaining(self):
        """Get time remaining before expiry."""
        if self.status != 'active':
            return timedelta(0)
        remaining = self.expires_at - timezone.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)
    
    def confirm(self):
        """Confirm reservation and reduce stock."""
        from .finance import confirm_reserved_sale
        sale = confirm_reserved_sale(self.pk)
        self.refresh_from_db()
        return sale
    
    def cancel(self):
        """Cancel reservation and release stock."""
        from .finance import update_reservation
        update_reservation(self.pk, cancel=True)
        self.refresh_from_db()
    
    def extend(self, minutes=1440):
        """Extend reservation expiry time."""
        from .finance import update_reservation
        update_reservation(self.pk, minutes=minutes)
        self.refresh_from_db()
    
    @classmethod
    def expire_old_reservations(cls):
        """Class method to expire old reservations."""
        expired = cls.objects.filter(
            status='active',
            expires_at__lt=timezone.now()
        )
        count = expired.count()
        expired.update(status='expired')
        return count


class FinanceAccount(models.Model):
    """A single row serializes ledger writes and partner reconciliations."""
    name = models.CharField(max_length=40, unique=True, default='main')


class Promotion(models.Model):
    ITEM_KINDS = ('percentage', 'amount', 'price')
    CART_KINDS = ('cart_percentage', 'cart_amount', 'cheapest_free', 'cart_extra_percent')
    KIND_CHOICES = [('percentage', 'Percentage off'), ('amount', 'Fixed amount off (€)'),
                    ('price', 'Promotional selling price (€)'),
                    ('cart_percentage', 'Buy N: percentage off eligible games'),
                    ('cart_extra_percent', 'Buy N: extra percentage off final prices'),
                    ('cart_amount', 'Buy N: fixed amount off eligible games (€)'),
                    ('cheapest_free', 'Buy N: cheapest eligible game free')]
    name = models.CharField(max_length=150)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default='percentage')
    value = models.DecimalField(max_digits=10, decimal_places=2)
    minimum_quantity = models.PositiveIntegerField(default=2)
    repeat_free_groups = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    apply_to_all = models.BooleanField(default=False)
    games = models.ManyToManyField(BoardGame, blank=True, related_name='promotions')
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True)
    description = models.TextField(blank=True, help_text='Optional customer-facing promotion terms')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at', '-id']
        constraints = [
            models.CheckConstraint(condition=models.Q(value__gte=0), name='promotion_value_nonnegative'),
            models.CheckConstraint(condition=models.Q(kind__in=['percentage', 'amount', 'price', 'cart_percentage', 'cart_amount', 'cheapest_free', 'cart_extra_percent']), name='promotion_kind_valid'),
            models.CheckConstraint(condition=~models.Q(kind__in=['percentage', 'cart_percentage', 'cart_extra_percent']) | models.Q(value__lte=100), name='promotion_percentage_valid'),
            models.CheckConstraint(condition=models.Q(minimum_quantity__gte=2, minimum_quantity__lte=100), name='promotion_quantity_valid'),
            models.CheckConstraint(condition=models.Q(ends_at__isnull=True) | models.Q(ends_at__gt=models.F('starts_at')), name='promotion_dates_valid'),
        ]

    def clean(self):
        if self.ends_at and self.starts_at and self.ends_at <= self.starts_at:
            raise ValidationError({'ends_at': 'The end must be after the start.'})
        if self.kind in ('percentage', 'cart_percentage', 'cart_extra_percent') and self.value is not None and self.value > 100:
            raise ValidationError({'value': 'Percentage discounts cannot exceed 100%.'})

    @property
    def is_cart_offer(self):
        return self.kind in self.CART_KINDS

    @property
    def mechanic_description(self):
        if self.kind == 'cheapest_free':
            return (f'Buy {self.minimum_quantity} eligible copies, pay for {self.minimum_quantity - 1}. '
                    + ('One free in every complete group.' if self.repeat_free_groups else 'One cheapest copy free per cart.'))
        if self.kind == 'cart_extra_percent':
            return f'Buy {self.minimum_quantity}+ eligible copies: an extra {self.value:g}% off final prices. Applied automatically at checkout.'
        if self.kind == 'cart_percentage':
            return f'Buy {self.minimum_quantity}+ eligible copies: {self.value:g}% off all eligible games.'
        if self.kind == 'cart_amount':
            return f'Buy {self.minimum_quantity}+ eligible copies: €{self.value:.2f} off the eligible subtotal.'
        if self.kind == 'percentage':
            return f'{self.value:g}% off each eligible game.'
        if self.kind == 'amount':
            return f'€{self.value:.2f} off each eligible game.'
        return f'Promotional selling price: €{self.value:.2f} per eligible game.'

    def price_for(self, base):
        if self.is_cart_offer:
            return base
        if self.kind == 'percentage':
            candidate = base * (Decimal('1') - self.value / Decimal('100'))
        elif self.kind == 'amount':
            candidate = base - self.value
        else:
            candidate = self.value
        return min(base, max(Decimal('0.00'), candidate.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)))

    @property
    def status(self):
        now = timezone.now()
        if not self.is_active:
            return 'Paused'
        if self.starts_at > now:
            return 'Scheduled'
        if self.ends_at and self.ends_at <= now:
            return 'Expired'
        return 'Active'

    def __str__(self):
        return self.name


class GameVideo(models.Model):
    game = models.ForeignKey(BoardGame, on_delete=models.CASCADE, related_name='videos')
    youtube_id = models.CharField(max_length=11)
    title = models.CharField(max_length=255)
    category = models.CharField(max_length=40, blank=True)
    language = models.CharField(max_length=40, default='English')
    source_url = models.URLField(max_length=500)
    imported_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['id']
        constraints = [models.UniqueConstraint(fields=['game', 'youtube_id'], name='unique_game_video')]

    @property
    def watch_url(self):
        return f'https://www.youtube.com/watch?v={self.youtube_id}'

    @property
    def embed_url(self):
        return f'https://www.youtube-nocookie.com/embed/{self.youtube_id}'


class Sale(models.Model):
    game = models.ForeignKey(BoardGame, on_delete=models.PROTECT, related_name='sales')
    game_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    customer_name = models.CharField(max_length=255, blank=True)
    reference = models.CharField(max_length=100, blank=True)
    sale_date = models.DateField(default=timezone.localdate)
    stock_deducted = models.BooleanField(default=True)
    reservation = models.OneToOneField(StockReservation, null=True, blank=True, on_delete=models.PROTECT)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        ordering = ['-sale_date', '-id']
        constraints = [
            models.CheckConstraint(condition=models.Q(quantity__gt=0), name='sale_quantity_positive'),
            models.CheckConstraint(condition=models.Q(unit_price__gte=0), name='sale_price_nonnegative'),
        ]

    @property
    def total(self):
        return self.unit_price * self.quantity

    @property
    def received(self):
        return sum((entry.signed_amount for entry in self.entries.all()), Decimal('0.00'))

    @property
    def outstanding(self):
        return self.total - self.received

    def __str__(self):
        return f'Sale #{self.pk} — {self.game_name}'


class CashEntry(models.Model):
    KIND_CHOICES = [('receipt', 'Payment received'), ('refund', 'Customer refund')]
    HOLDER_CHOICES = [('business', 'Me / business'), ('partner', 'Partner')]
    METHOD_CHOICES = [('cash', 'Cash'), ('bank', 'Bank transfer'), ('card', 'Card'), ('other', 'Other')]
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='entries')
    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    holder = models.CharField(max_length=10, choices=HOLDER_CHOICES, default='business')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.localdate)
    method = models.CharField(max_length=10, choices=METHOD_CHOICES, default='cash')
    reference = models.CharField(max_length=150, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        ordering = ['-date', '-id']
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name='cash_amount_positive'),
            models.CheckConstraint(condition=models.Q(kind__in=['receipt', 'refund']), name='cash_kind_valid'),
            models.CheckConstraint(condition=models.Q(holder__in=['business', 'partner']), name='cash_holder_valid'),
        ]

    @property
    def signed_amount(self):
        return self.amount if self.kind == 'receipt' else -self.amount


class PartnerTransfer(models.Model):
    DIRECTION_CHOICES = [('to_partner', 'Paid to partner'), ('from_partner', 'Received from partner')]
    direction = models.CharField(max_length=20, choices=DIRECTION_CHOICES, default='to_partner')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.localdate)
    reference = models.CharField(max_length=150)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    request_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    class Meta:
        ordering = ['-date', '-id']
        constraints = [
            models.CheckConstraint(condition=models.Q(amount__gt=0), name='transfer_amount_positive'),
            models.CheckConstraint(condition=models.Q(direction__in=['to_partner', 'from_partner']), name='transfer_direction_valid'),
        ]

    @property
    def signed_amount(self):
        return self.amount if self.direction == 'to_partner' else -self.amount
