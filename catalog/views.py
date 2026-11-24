"""
Public catalog views - Browse games, view details, search.
"""

from django.shortcuts import render, get_object_or_404
from decimal import Decimal, InvalidOperation
from django.core.paginator import Paginator
from django.db.models import Q, F, Case, When, DecimalField, FloatField
from django.db.models.functions import Cast, Round
from .models import BoardGame
from .pricing import with_selling_price
from .cart_pricing import active_cart_offers
from .engagement import count_product_click


def public_catalog(request):
    """Display public catalog with filtering and search."""
    games = with_selling_price(BoardGame.objects.all())
    availability = request.GET.get('availability', 'all')
    if availability == 'available':
        games = games.filter(is_sold=False, stock_quantity__gt=0)
    elif availability == 'sold_out':
        games = games.filter(Q(is_sold=True) | Q(stock_quantity=0))
    else:
        availability = 'all'
    
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
            value = Decimal(min_price)
            if value.is_finite() and value >= 0:
                games = games.filter(selling_price__gte=value)
        except InvalidOperation:
            pass
    if max_price:
        try:
            value = Decimal(max_price)
            if value.is_finite() and value >= 0:
                games = games.filter(selling_price__lte=value)
        except InvalidOperation:
            pass
    
    # Sort options
    sort_by = request.GET.get('sort', 'relevance')
    sort_by = {'msrp_price': 'selling_price', '-msrp_price': '-selling_price'}.get(sort_by, sort_by)
    if sort_by not in ['relevance', 'name', '-name', 'selling_price', '-selling_price', '-created_at', 'year_published']:
        sort_by = 'relevance'
    if sort_by == 'relevance':
        games = games.order_by('-click_count', F('rating_average').desc(nulls_last=True), 'id')
    elif sort_by.lstrip('-') == 'selling_price':
        expression = F('selling_price')
        games = games.order_by(expression.desc(nulls_last=True) if sort_by.startswith('-') else expression.asc(nulls_last=True), 'id')
    else:
        games = games.order_by(sort_by, 'id')
    page = Paginator(games, 24).get_page(request.GET.get('page'))
    
    context = {
        'games': page.object_list,
        'page_obj': page,
        'availability': availability,
        'has_filters': bool(condition or min_price or max_price or sort_by != 'relevance' or availability != 'all'),
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
    count_product_click(request, game)
    
    # Check if game has active cart items in session
    cart = request.session.get('cart', {})
    in_cart = str(game_id) in cart
    cart_quantity = cart.get(str(game_id), 0)
    
    context = {
        'game': game,
        'in_cart': in_cart,
        'cart_quantity': cart_quantity,
        'videos': game.videos.filter(is_active=True),
        'cart_offers': [offer for offer in active_cart_offers()
                        if offer.apply_to_all or game.pk in {g.pk for g in offer.games.all()}],
    }
    
    return render(request, 'catalog/game_detail.html', context)
