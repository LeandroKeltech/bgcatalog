from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.db.models import Sum
import json


class BoardGame(models.Model):
    """Board Game model for catalog management"""
    
    CONDITION_CHOICES = [
        ('new', 'New'),
        ('like_new', 'Like New'),
        ('used', 'Used'),
        ('damaged', 'Damaged'),
        ('missing_pieces', 'Missing Pieces'),
    ]
    
    # BGG Information
    bgg_id = models.IntegerField(unique=True, null=True, blank=True, help_text="BoardGameGeek ID")
    name = models.CharField(max_length=255, help_text="Game name")
    description = models.TextField(blank=True, help_text="Game description")
    year_published = models.IntegerField(null=True, blank=True, help_text="Year published")
    
    # Game Details
    designer = models.CharField(max_length=255, blank=True, help_text="Game designer(s)")
    min_players = models.IntegerField(null=True, blank=True, help_text="Minimum players")
    max_players = models.IntegerField(null=True, blank=True, help_text="Maximum players")
    min_playtime = models.IntegerField(null=True, blank=True, help_text="Minimum playtime (minutes)")
    max_playtime = models.IntegerField(null=True, blank=True, help_text="Maximum playtime (minutes)")
    min_age = models.IntegerField(null=True, blank=True, help_text="Minimum age")
    
    # Pricing
    msrp_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Manufacturer's Suggested Retail Price (MSRP)"
    )
    
    # Condition & Discount
    condition = models.CharField(
        max_length=20, 
        choices=CONDITION_CHOICES, 
        default='new',
        help_text="Game condition"
    )
    discount_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=30.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Discount percentage (0-100)"
    )
    
    # Calculated Fields
    final_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Final price after discount"
    )
    
    # Inventory
    stock_quantity = models.IntegerField(
        default=1,
        validators=[MinValueValidator(0)],
        help_text="Available quantity in stock"
    )
    is_sold = models.BooleanField(default=False, help_text="Mark as sold")
    sold_date = models.DateTimeField(null=True, blank=True, help_text="Date when sold")
    
    # Images (stored as JSON array of URLs)
    images_urls = models.TextField(blank=True, help_text="JSON array of image URLs")
    thumbnail_url = models.URLField(max_length=500, blank=True, help_text="Main thumbnail URL")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Additional Notes
    notes = models.TextField(blank=True, help_text="Additional notes about the game")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Board Game"
        verbose_name_plural = "Board Games"
    
    def __str__(self):
        return f"{self.name} ({self.year_published or 'N/A'})"
    
    def save(self, *args, **kwargs):
        """Override save to calculate final price and handle sold logic"""
        # Calculate final price based on MSRP and discount
        if self.msrp_price and self.discount_percentage is not None:
            discount_amount = self.msrp_price * (self.discount_percentage / 100)
            self.final_price = self.msrp_price - discount_amount
        
        # Set default discount based on condition if not manually set
        if not self.pk:  # Only on creation
            condition_defaults = {
                'new': 30.00,
                'like_new': 50.00,
                'used': 70.00,
                'damaged': 80.00,
                'missing_pieces': 85.00,
            }
            if self.condition in condition_defaults and self.discount_percentage == 30.00:
                self.discount_percentage = condition_defaults[self.condition]
        
        # Mark sold date
        if self.is_sold and not self.sold_date:
            self.sold_date = timezone.now()
        elif not self.is_sold:
            self.sold_date = None
        
        # Adjust stock when marked as sold
        if self.is_sold and self.stock_quantity > 0:
            self.stock_quantity = 0
        
        super().save(*args, **kwargs)
    
    def get_images_list(self):
        """Parse images URLs from JSON string"""
        if self.images_urls:
            try:
                return json.loads(self.images_urls)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_images_list(self, images_list):
        """Set images URLs from list"""
        self.images_urls = json.dumps(images_list)
    
    @property
    def players_range(self):
        """Return player range as string"""
        if self.min_players and self.max_players:
            if self.min_players == self.max_players:
                return f"{self.min_players}"
            return f"{self.min_players}-{self.max_players}"
        elif self.min_players:
            return f"{self.min_players}+"
        return "N/A"
    
    @property
    def playtime_range(self):
        """Return playtime range as string"""
        if self.min_playtime and self.max_playtime:
            if self.min_playtime == self.max_playtime:
                return f"{self.min_playtime} min"
            return f"{self.min_playtime}-{self.max_playtime} min"
        elif self.min_playtime:
            return f"{self.min_playtime}+ min"
        return "N/A"
    
    @property
    def in_stock(self):
        """Check if game is in stock"""
        return self.stock_quantity > 0 and not self.is_sold
    
    @property
    def available_quantity(self):
        """Get available quantity considering reservations"""
        reserved = self.get_reserved_quantity()
        return max(0, self.stock_quantity - reserved)
    
    def get_reserved_quantity(self):
        """Get total reserved quantity for this game"""
        from django.utils import timezone
        return self.stockreservation_set.filter(
            expires_at__gt=timezone.now(),
            status='active'
        ).aggregate(
            total=Sum('quantity')
        )['total'] or 0
    
    @property
    def is_available(self):
        """Check if game is available for purchase (considering reservations)"""
        return self.available_quantity > 0 and not self.is_sold


class CartItem(models.Model):
    """Shopping cart item"""
    session_key = models.CharField(max_length=40, help_text="Session ID for anonymous users")
    game = models.ForeignKey(BoardGame, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['session_key', 'game']
    
    def __str__(self):
        return f"{self.game.name} x{self.quantity}"
    
    @property
    def subtotal(self):
        """Calculate subtotal for this item"""
        if self.game.final_price:
            return self.game.final_price * self.quantity
        return 0


class StockReservation(models.Model):
    """Model to track temporary stock reservations when users request quotes"""
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('confirmed', 'Confirmed Sale'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    ]
    
    game = models.ForeignKey(BoardGame, on_delete=models.CASCADE, help_text="Reserved game")
    quantity = models.IntegerField(validators=[MinValueValidator(1)], help_text="Reserved quantity")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Customer information from quote request
    customer_name = models.CharField(max_length=255, help_text="Customer name")
    customer_email = models.EmailField(help_text="Customer email")
    customer_phone = models.CharField(max_length=50, blank=True, help_text="Customer phone")
    customer_message = models.TextField(blank=True, help_text="Customer message")
    
    # Session tracking
    session_key = models.CharField(max_length=40, help_text="Session ID")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, help_text="When reservation was created")
    expires_at = models.DateTimeField(help_text="When reservation expires")
    confirmed_at = models.DateTimeField(null=True, blank=True, help_text="When sale was confirmed")
    
    # Admin notes
    admin_notes = models.TextField(blank=True, help_text="Admin notes about this reservation")
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Stock Reservation"
        verbose_name_plural = "Stock Reservations"
    
    def __str__(self):
        return f"{self.game.name} x{self.quantity} - {self.customer_name} ({self.status})"
    
    def save(self, *args, **kwargs):
        """Set expiration time if not set"""
        if not self.expires_at:
            # Default: 30 minutes from creation
            self.expires_at = timezone.now() + timezone.timedelta(minutes=30)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if reservation has expired"""
        return timezone.now() > self.expires_at
    
    @property
    def time_remaining(self):
        """Get remaining time for reservation"""
        if self.is_expired:
            return timezone.timedelta(0)
        return self.expires_at - timezone.now()
    
    def confirm_sale(self, admin_notes=""):
        """Confirm the sale and reduce actual stock"""
        if self.status != 'active':
            raise ValueError("Can only confirm active reservations")
        
        # Check if there's still enough stock
        if self.game.stock_quantity < self.quantity:
            raise ValueError("Not enough stock to confirm sale")
        
        # Update reservation
        self.status = 'confirmed'
        self.confirmed_at = timezone.now()
        if admin_notes:
            self.admin_notes = admin_notes
        self.save()
        
        # Reduce actual stock
        self.game.stock_quantity -= self.quantity
        if self.game.stock_quantity == 0:
            self.game.is_sold = True
        self.game.save()
    
    def cancel_reservation(self, admin_notes=""):
        """Cancel the reservation and free up stock"""
        if self.status not in ['active', 'expired']:
            raise ValueError("Can only cancel active or expired reservations")
        
        self.status = 'cancelled'
        if admin_notes:
            self.admin_notes = admin_notes
        self.save()
    
    def extend_reservation(self, minutes=30):
        """Extend reservation time"""
        if self.status != 'active':
            raise ValueError("Can only extend active reservations")
        
        self.expires_at = timezone.now() + timezone.timedelta(minutes=minutes)
        self.save()
    
    @classmethod
    def cleanup_expired(cls):
        """Cleanup expired reservations"""
        expired_reservations = cls.objects.filter(
            status='active',
            expires_at__lt=timezone.now()
        )
        
        count = expired_reservations.count()
        expired_reservations.update(status='expired')
        
        return count
