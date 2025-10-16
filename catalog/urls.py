from django.urls import path
from . import views
from . import cart_views

urlpatterns = [
    # Main catalog (admin)
    path('', views.index, name='index'),
    path('catalog/', views.catalog_list, name='catalog_list'),
    path('game/<int:pk>/', views.game_detail, name='game_detail'),
    
    # BGG Integration
    path('bgg/search/', views.bgg_search, name='bgg_search'),
    path('bgg/import/<str:bgg_id>/', views.bgg_import, name='bgg_import'),
    
    # CRUD Operations
    path('game/create/', views.game_create_manual, name='game_create_manual'),
    path('game/<int:pk>/edit/', views.game_edit, name='game_edit'),
    path('game/<int:pk>/delete/', views.game_delete, name='game_delete'),
    path('game/<int:pk>/mark-sold/', views.game_mark_sold, name='game_mark_sold'),
    path('game/<int:pk>/unmark-sold/', views.game_unmark_sold, name='game_unmark_sold'),
    
    # Google Sheets Sync
    path('sync-to-sheets/', views.sync_to_sheets, name='sync_to_sheets'),
    
    # Public Catalog
    path('public/', views.public_catalog, name='public_catalog'),
    path('public/game/<int:pk>/', views.public_game_detail, name='public_game_detail'),
    
    # Shopping Cart
    path('cart/', cart_views.cart_view, name='cart_view'),
    path('cart/add/<int:pk>/', cart_views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:pk>/', cart_views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:pk>/', cart_views.update_cart_quantity, name='update_cart_quantity'),
    path('cart/send/', cart_views.send_cart_email, name='send_cart_email'),
    
    # Admin Panel
    path('admin-login/', cart_views.admin_login, name='admin_login'),
    path('admin-logout/', cart_views.admin_logout, name='admin_logout'),
    path('admin-panel/', cart_views.admin_panel, name='admin_panel'),
]
