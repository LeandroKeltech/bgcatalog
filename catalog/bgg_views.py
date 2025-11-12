"""
BGG/BGA search and import views.
"""

from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.http import JsonResponse
from .models import BoardGame
from . import bgg_price_service
import logging

logger = logging.getLogger(__name__)


@staff_member_required
def bgg_search(request):
    """Search BGG/BGA for games."""
    search_query = request.GET.get('search', '')
    games = []
    
    if search_query:
        # Check if this is a barcode (numeric, 12-13 digits)
        is_barcode = search_query.isdigit() and len(search_query) in [12, 13]

        # Search using the service
        games = bgg_price_service.search_bgg_games(search_query, exact=is_barcode)

        # Populate thumbnails for results that lack them by fetching BGG thing thumbnail.
        # This adds a few extra API calls but greatly improves UX in the admin search.
        for g in games:
            if not g.get('thumbnail') and g.get('bgg_id') and not g.get('bgg_id').startswith('bga_'):
                try:
                    thumb = bgg_price_service.fetch_bgg_thumbnail(g['bgg_id'])
                    if thumb:
                        g['thumbnail'] = thumb
                        logger.info(f"Fetched thumbnail for BGG id {g.get('bgg_id')}: {thumb}")
                except Exception as e:
                    logger.warning(f"Failed to fetch thumbnail for {g.get('bgg_id')}: {e}")
                    continue
    
    context = {
        'search_query': search_query,
        'games': games,
    }
    
    return render(request, 'catalog/bgg_search.html', context)


@staff_member_required
def import_from_bgg(request, bgg_id):
    """Import game details from BGG/BGA and create new game entry."""
    if request.method != 'POST':
        return redirect('bgg_search')
    
    # Check if game already exists
    existing_game = BoardGame.objects.filter(bgg_id=bgg_id).first()
    if existing_game:
        messages.warning(request, f'Game already exists: {existing_game.name}')
        return redirect('edit_game', game_id=existing_game.id)
    
    # Fetch game details
    game_data = bgg_price_service.get_bgg_game_details(bgg_id)
    
    if not game_data:
        # Try a few graceful fallbacks so the admin can still import a minimal record
        messages.warning(request, 'Primary fetch failed — attempting lightweight fallbacks')
        try:
            # If this looks like a BGA id, try the BGA details directly
            if bgg_id.startswith('bga_'):
                bga_id = bgg_id[4:]
                game_data = bgg_price_service.get_bga_game_details(bga_id)
        except Exception as e:
            # swallow and continue to other fallbacks
            game_data = {}

    # If we still have no detailed data, try to at least fetch a thumbnail and set a name
    if not game_data:
        try:
            # If numeric BGG id, try fetching thumbnail
            if bgg_id.isdigit():
                thumb = bgg_price_service.fetch_bgg_thumbnail(bgg_id)
                game_data = {
                    'name': f'BGG #{bgg_id}',
                    'image_url': thumb or '',
                    'thumbnail_url': thumb or '',
                    'description': '',
                }
                messages.info(request, f'Imported minimal record for BGG id {bgg_id}')
            else:
                # As a last resort create minimal record with id as name
                game_data = {'name': bgg_id, 'image_url': '', 'thumbnail_url': '', 'description': ''}
                messages.info(request, 'Imported minimal record using id as name')
        except Exception as e:
            messages.error(request, f'Failed to fetch fallback data: {e}')
            return redirect('bgg_search')
    
    # Fetch pricing
    pricing = bgg_price_service.fetch_boardgameprices(bgg_id)
    if pricing:
        game_data['msrp_price'] = pricing.get('price')
    
    # Create new game
    game = BoardGame.objects.create(
        bgg_id=bgg_id,
        name=game_data.get('name', 'Unknown Game'),
        year_published=game_data.get('year_published'),
        designer=game_data.get('designer', ''),
        description=game_data.get('description', ''),
        image_url=game_data.get('image_url', ''),
        thumbnail_url=game_data.get('thumbnail_url', ''),
        min_players=game_data.get('min_players'),
        max_players=game_data.get('max_players'),
        min_playtime=game_data.get('min_playtime'),
        max_playtime=game_data.get('max_playtime'),
        min_age=game_data.get('min_age'),
        categories=game_data.get('categories', ''),
        mechanics=game_data.get('mechanics', ''),
        rating_average=game_data.get('rating_average'),
        rating_bayes=game_data.get('rating_bayes'),
        rank_overall=game_data.get('rank_overall'),
        num_ratings=game_data.get('num_ratings'),
        msrp_price=game_data.get('msrp_price'),
        stock_quantity=1,
        condition='new',
    )
    
    messages.success(request, f'Game "{game.name}" imported successfully!')
    return redirect('edit_game', game_id=game.id)


@staff_member_required
def refresh_game_data(request, game_id):
    """Refresh game data from BGG/BGA."""
    game = BoardGame.objects.get(id=game_id)
    
    if not game.bgg_id:
        messages.error(request, 'Game has no BGG/BGA ID to refresh from')
        return redirect('edit_game', game_id=game_id)
    
    # Fetch updated data
    game_data = bgg_price_service.get_bgg_game_details(game.bgg_id)
    
    if not game_data:
        messages.error(request, 'Failed to fetch updated game details')
        return redirect('edit_game', game_id=game_id)
    
    # Update fields (preserve manual edits to certain fields)
    game.name = game_data.get('name', game.name)
    game.year_published = game_data.get('year_published') or game.year_published
    game.designer = game_data.get('designer', game.designer)
    game.description = game_data.get('description', game.description)
    game.image_url = game_data.get('image_url', game.image_url)
    game.thumbnail_url = game_data.get('thumbnail_url', game.thumbnail_url)
    game.min_players = game_data.get('min_players') or game.min_players
    game.max_players = game_data.get('max_players') or game.max_players
    game.min_playtime = game_data.get('min_playtime') or game.min_playtime
    game.max_playtime = game_data.get('max_playtime') or game.max_playtime
    game.min_age = game_data.get('min_age') or game.min_age
    game.categories = game_data.get('categories', game.categories)
    game.mechanics = game_data.get('mechanics', game.mechanics)
    game.rating_average = game_data.get('rating_average') or game.rating_average
    game.rating_bayes = game_data.get('rating_bayes') or game.rating_bayes
    game.rank_overall = game_data.get('rank_overall') or game.rank_overall
    game.num_ratings = game_data.get('num_ratings') or game.num_ratings
    
    # Update pricing if available
    pricing = bgg_price_service.fetch_boardgameprices(game.bgg_id)
    if pricing and not game.msrp_price:
        game.msrp_price = pricing.get('price')
    
    game.save()
    messages.success(request, f'Game "{game.name}" refreshed successfully!')
    return redirect('edit_game', game_id=game_id)
