"""
Public catalog views - Browse games, view details, search.
"""

from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .models import BoardGame


def public_catalog(request):
    """Display public catalog with filtering and search."""
    games = BoardGame.objects.filter(is_sold=False, stock_quantity__gt=0)
    
    # Search query
    search_query = request.GET.get('search', '')
    if search_query:
        games = games.filter(
            Q(name__icontains=search_query) |
            Q(designer__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Filter by condition
    condition = request.GET.get('condition', '')
    if condition:
        games = games.filter(condition=condition)
    
    # Filter by price range
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    if min_price:
        try:
            games = games.filter(msrp_price__gte=float(min_price))
        except ValueError:
            pass
    if max_price:
        try:
            games = games.filter(msrp_price__lte=float(max_price))
        except ValueError:
            pass
    
    # Sort options
    sort_by = request.GET.get('sort', '-created_at')
    if sort_by in ['name', '-name', 'msrp_price', '-msrp_price', '-created_at', 'year_published']:
        games = games.order_by(sort_by)
    
    context = {
        'games': games,
        'search_query': search_query,
        'condition': condition,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
        'condition_choices': BoardGame.CONDITION_CHOICES,
    }
    
    return render(request, 'catalog/public_catalog.html', context)


def game_detail(request, game_id):
    """Display detailed game information."""
    game = get_object_or_404(BoardGame, id=game_id)
    
    # Check if game has active cart items in session
    cart = request.session.get('cart', {})
    in_cart = str(game_id) in cart
    cart_quantity = cart.get(str(game_id), 0)
    
    context = {
        'game': game,
        'in_cart': in_cart,
        'cart_quantity': cart_quantity,
    }
    
    return render(request, 'catalog/game_detail.html', context)
