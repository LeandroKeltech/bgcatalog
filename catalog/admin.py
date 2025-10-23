from django.contrib import admin
from .models import BoardGame, StockReservation


@admin.register(BoardGame)
class BoardGameAdmin(admin.ModelAdmin):
    list_display = ['name', 'year_published', 'condition', 'msrp_price', 'discount_percentage', 'final_price', 'stock_quantity', 'is_sold', 'created_at']
    list_filter = ['condition', 'is_sold', 'year_published']
    search_fields = ['name', 'designer', 'description']
    readonly_fields = ['final_price', 'created_at', 'updated_at', 'sold_date']
    
    fieldsets = (
        ('BGG Information', {
            'fields': ('bgg_id', 'name', 'description', 'year_published')
        }),
        ('Game Details', {
            'fields': ('designer', 'min_players', 'max_players', 'min_playtime', 'max_playtime', 'min_age')
        }),
        ('Pricing & Condition', {
            'fields': ('condition', 'msrp_price', 'discount_percentage', 'final_price')
        }),
        ('Inventory', {
            'fields': ('stock_quantity', 'is_sold', 'sold_date')
        }),
        ('Images', {
            'fields': ('thumbnail_url', 'images_urls')
        }),
        ('Additional Info', {
            'fields': ('notes', 'created_at', 'updated_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        """Override save to trigger Google Sheets sync"""
        super().save_model(request, obj, form, change)
        
        # Try to sync to Google Sheets
        try:
            from .sheets_service import GoogleSheetsService
            sheets = GoogleSheetsService()
            if sheets.authenticate() and sheets.get_or_create_spreadsheet():
                sheets.sync_game_to_sheet(obj)
        except:
            pass  # Don't fail if sheets sync fails


@admin.register(StockReservation)
class StockReservationAdmin(admin.ModelAdmin):
    list_display = ['game', 'quantity', 'customer_name', 'customer_email', 'status', 'created_at', 'expires_at', 'time_remaining_display']
    list_filter = ['status', 'created_at', 'expires_at']
    search_fields = ['game__name', 'customer_name', 'customer_email']
    readonly_fields = ['created_at', 'confirmed_at', 'time_remaining_display', 'is_expired']
    
    fieldsets = (
        ('Reservation Details', {
            'fields': ('game', 'quantity', 'status', 'created_at', 'expires_at', 'confirmed_at')
        }),
        ('Customer Information', {
            'fields': ('customer_name', 'customer_email', 'customer_phone', 'customer_message', 'session_key')
        }),
        ('Status', {
            'fields': ('is_expired', 'time_remaining_display')
        }),
        ('Admin Notes', {
            'fields': ('admin_notes',)
        }),
    )
    
    def time_remaining_display(self, obj):
        """Display time remaining in human readable format"""
        if obj.is_expired:
            return "EXPIRED"
        remaining = obj.time_remaining
        if remaining.total_seconds() > 0:
            minutes = int(remaining.total_seconds() // 60)
            return f"{minutes} minutes"
        return "EXPIRED"
    time_remaining_display.short_description = "Time Remaining"
    
    actions = ['confirm_selected_reservations', 'cancel_selected_reservations', 'extend_selected_reservations']
    
    def confirm_selected_reservations(self, request, queryset):
        """Confirm selected reservations"""
        confirmed = 0
        errors = []
        
        for reservation in queryset.filter(status='active'):
            try:
                reservation.confirm_sale()
                confirmed += 1
            except Exception as e:
                errors.append(f"{reservation}: {str(e)}")
        
        if confirmed:
            self.message_user(request, f"Successfully confirmed {confirmed} reservations.")
        if errors:
            self.message_user(request, f"Errors: {'; '.join(errors)}", level='ERROR')
    
    confirm_selected_reservations.short_description = "Confirm selected reservations"
    
    def cancel_selected_reservations(self, request, queryset):
        """Cancel selected reservations"""
        cancelled = 0
        
        for reservation in queryset.filter(status__in=['active', 'expired']):
            try:
                reservation.cancel_reservation()
                cancelled += 1
            except Exception as e:
                pass
        
        if cancelled:
            self.message_user(request, f"Successfully cancelled {cancelled} reservations.")
    
    cancel_selected_reservations.short_description = "Cancel selected reservations"
    
    def extend_selected_reservations(self, request, queryset):
        """Extend selected reservations by 30 minutes"""
        extended = 0
        
        for reservation in queryset.filter(status='active'):
            try:
                reservation.extend_reservation(30)
                extended += 1
            except Exception as e:
                pass
        
        if extended:
            self.message_user(request, f"Successfully extended {extended} reservations by 30 minutes.")
    
    extend_selected_reservations.short_description = "Extend selected reservations by 30 minutes"
