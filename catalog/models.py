from django.db import models
from django.utils import timezone
from datetime import timedelta


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
    ]
    
    # Basic Information
    name = models.CharField(max_length=255, help_text="Game name")
    bgg_id = models.CharField(
        max_length=50, 
        unique=True, 
        null=True, 
        blank=True,
        help_text="BoardGameGeek ID or BGA ID (prefixed with 'bga_')"
    )
    year_published = models.IntegerField(null=True, blank=True, help_text="Year published")
    designer = models.CharField(max_length=255, blank=True, help_text="Game designer(s)")
    description = models.TextField(blank=True, help_text="Game description")
    
    # Images
    image_url = models.URLField(max_length=500, blank=True, help_text="Full-size image URL")
    thumbnail_url = models.URLField(max_length=500, blank=True, help_text="Thumbnail image URL")
    
    # Gameplay Details
    min_players = models.IntegerField(null=True, blank=True, help_text="Minimum number of players")
    max_players = models.IntegerField(null=True, blank=True, help_text="Maximum number of players")
    min_playtime = models.IntegerField(null=True, blank=True, help_text="Minimum playtime (minutes)")
    max_playtime = models.IntegerField(null=True, blank=True, help_text="Maximum playtime (minutes)")
    min_age = models.IntegerField(null=True, blank=True, help_text="Minimum recommended age")
    
    # Categories and Mechanics
    categories = models.CharField(max_length=500, blank=True, help_text="Comma-separated categories")
    mechanics = models.CharField(max_length=500, blank=True, help_text="Comma-separated mechanics")
    
    # Ratings
    rating_average = models.FloatField(null=True, blank=True, help_text="Average user rating")
    rating_bayes = models.FloatField(null=True, blank=True, help_text="Bayes average rating")
    rank_overall = models.IntegerField(null=True, blank=True, help_text="Overall BGG rank")
    num_ratings = models.IntegerField(null=True, blank=True, help_text="Number of ratings")
    
    # Pricing
    msrp_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="MSRP price in EUR"
    )
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
        indexes = [
            models.Index(fields=['bgg_id']),
            models.Index(fields=['name']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_sold']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.year_published or 'N/A'})"
    
    @property
    def final_price(self):
        """Calculate final price after discount."""
        if self.msrp_price:
            discount_multiplier = 1 - (self.discount_percentage / 100)
            return round(self.msrp_price * discount_multiplier, 2)
        return None
    
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
        if self.is_sold and not self.sold_date:
            self.sold_date = timezone.now()
        elif not self.is_sold:
            self.sold_date = None
        super().save(*args, **kwargs)


class StockReservation(models.Model):
    """
    Model for managing temporary stock reservations during checkout.
    Prevents overselling by holding stock for 30 minutes.
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
        on_delete=models.CASCADE,
        related_name='reservations',
        help_text="Reserved game"
    )
    quantity = models.IntegerField(default=1, help_text="Reserved quantity")
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
            self.expires_at = timezone.now() + timedelta(minutes=30)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if reservation has expired."""
        return timezone.now() > self.expires_at and self.status == 'active'
    
    @property
    def time_remaining(self):
        """Get time remaining before expiry."""
        if self.status != 'active':
            return timedelta(0)
        remaining = self.expires_at - timezone.now()
        return remaining if remaining.total_seconds() > 0 else timedelta(0)
    
    def confirm(self):
        """Confirm reservation and reduce stock."""
        if self.status != 'active':
            raise ValueError("Can only confirm active reservations")
        
        self.status = 'confirmed'
        self.confirmed_at = timezone.now()
        self.save()
        
        # Reduce stock quantity
        self.game.stock_quantity -= self.quantity
        if self.game.stock_quantity <= 0:
            self.game.is_sold = True
        self.game.save()
    
    def cancel(self):
        """Cancel reservation and release stock."""
        if self.status == 'confirmed':
            raise ValueError("Cannot cancel confirmed reservations")
        
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.save()
    
    def extend(self, minutes=30):
        """Extend reservation expiry time."""
        if self.status != 'active':
            raise ValueError("Can only extend active reservations")
        
        self.expires_at = timezone.now() + timedelta(minutes=minutes)
        self.save()
    
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
