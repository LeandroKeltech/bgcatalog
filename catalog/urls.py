"""
URL routing for catalog app.
"""

from django.urls import path
from . import views, admin_views, bgg_views, cart_views, finance_views
from . import promotion_views
from . import customer_views
from . import notification_views

urlpatterns = [
    # Public catalog
    path('', views.public_catalog, name='public_catalog'),
    path('catalog/', views.public_catalog, name='catalog'),
    path('game/<int:game_id>/', views.game_detail, name='game_detail'),
    path('account/register/', customer_views.customer_register, name='customer_register'),
    path('account/login/', customer_views.customer_login, name='customer_login'),
    path('account/logout/', customer_views.customer_logout, name='customer_logout'),
    path('account/', customer_views.customer_account, name='customer_account'),
    path('account/quotes/<uuid:quote_id>/', customer_views.customer_quote, name='customer_quote'),
    
    # Admin panel
    path('admin-panel/notifications/', notification_views.notification_list, name='notification_list'),
    path('admin-panel/notifications/status/', notification_views.notification_status, name='notification_status'),
    path('admin-panel/notifications/<int:notification_id>/open/', notification_views.notification_open, name='notification_open'),
    path('admin-panel/notifications/<int:notification_id>/retry-email/', notification_views.notification_retry_email, name='notification_retry_email'),
    path('admin-panel/', admin_views.admin_panel, name='admin_panel'),
    path('admin-panel/promotions/', promotion_views.promotion_list, name='promotion_list'),
    path('admin-panel/promotions/new/', promotion_views.promotion_edit, name='promotion_new'),
    path('admin-panel/promotions/<int:promotion_id>/edit/', promotion_views.promotion_edit, name='promotion_edit'),
    path('admin-panel/promotions/<int:promotion_id>/toggle/', promotion_views.promotion_toggle, name='promotion_toggle'),
    path('admin-panel/game/new/', admin_views.new_game, name='new_game'),
    path('admin-panel/finances/', finance_views.finance_dashboard, name='finance_dashboard'),
    path('admin-panel/finances/sale/new/', finance_views.new_sale, name='new_sale'),
    path('admin-panel/finances/sale/<int:sale_id>/', finance_views.sale_detail, name='sale_detail'),
    path('admin-panel/finances/transfer/', finance_views.partner_transfer, name='partner_transfer'),
    path('admin-panel/finances/export/', finance_views.finance_export, name='finance_export'),
    path('admin-panel/game/<int:game_id>/edit/', admin_views.edit_game, name='edit_game'),
    path('admin-panel/game/<int:game_id>/delete/', admin_views.delete_game, name='delete_game'),
    
    # BGG search and import
    path('admin-panel/bgg-search/', bgg_views.bgg_search, name='bgg_search'),
    path('admin-panel/preview/<str:bgg_id>/', bgg_views.preview_bgg_game, name='preview_bgg_game'),
    path('admin-panel/import/<str:bgg_id>/', bgg_views.import_from_bgg, name='import_from_bgg'),
    path('admin-panel/game/<int:game_id>/refresh/', bgg_views.refresh_game_data, name='refresh_game_data'),
    
    # Reservations
    path('admin-panel/reservations/', admin_views.reservation_management, name='reservation_management'),
    path('admin-panel/reservations/<int:reservation_id>/confirm/', admin_views.confirm_reservation, name='confirm_reservation'),
    path('admin-panel/reservations/<int:reservation_id>/cancel/', admin_views.cancel_reservation, name='cancel_reservation'),
    path('admin-panel/reservations/<int:reservation_id>/extend/', admin_views.extend_reservation, name='extend_reservation'),
    
    # Cart and checkout
    path('cart/', cart_views.view_cart, name='view_cart'),
    path('cart/add/<int:game_id>/', cart_views.add_to_cart, name='add_to_cart'),
    path('cart/update/<int:game_id>/', cart_views.update_cart, name='update_cart'),
    path('cart/remove/<int:game_id>/', cart_views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', cart_views.checkout, name='checkout'),
    path('checkout/success/', cart_views.checkout_success, name='checkout_success'),
]
