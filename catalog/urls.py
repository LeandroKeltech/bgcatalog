"""
URL routing for catalog app.
"""

from django.urls import path
from . import views, admin_views, bgg_views, cart_views

urlpatterns = [
    # Public catalog
    path('', views.public_catalog, name='public_catalog'),
    path('catalog/', views.public_catalog, name='catalog'),
    path('game/<int:game_id>/', views.game_detail, name='game_detail'),
    
    # Admin panel
    path('admin-panel/', admin_views.admin_panel, name='admin_panel'),
    path('admin-panel/game/<int:game_id>/edit/', admin_views.edit_game, name='edit_game'),
    path('admin-panel/game/<int:game_id>/delete/', admin_views.delete_game, name='delete_game'),
    
    # BGG search and import
    path('admin-panel/bgg-search/', bgg_views.bgg_search, name='bgg_search'),
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
