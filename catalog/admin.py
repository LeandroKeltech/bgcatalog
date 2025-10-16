from django.contrib import admin
from .models import BoardGame


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
