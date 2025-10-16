from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import ensure_csrf_cookie
from django.middleware.csrf import get_token
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.conf import settings
from .models import BoardGame, CartItem
from .bgg_service import BGGService
from .bga_service import search_games as bga_search_games, get_game_details as bga_get_game_details
from .bgg_price_service import search_bgg_games, get_bgg_game_details
from .sheets_service import GoogleSheetsService
from decimal import Decimal
import json
import logging

logger = logging.getLogger(__name__)


def index(request):
    """Home page - redirect to public catalog"""
    return redirect('public_catalog')


@ensure_csrf_cookie
def catalog_list(request):
    """List all board games in catalog with filters"""
    # Explicitly generate CSRF token
    get_token(request)
    
    games = BoardGame.objects.all()
    
    # Search filter
    search_query = request.GET.get('search', '')
    if search_query:
        games = games.filter(
            Q(name__icontains=search_query) |
            Q(designer__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Condition filter
    condition = request.GET.get('condition', '')
    if condition:
        games = games.filter(condition=condition)
    
    # Stock filter
    stock_filter = request.GET.get('stock', '')
    if stock_filter == 'in_stock':
        games = games.filter(stock_quantity__gt=0, is_sold=False)
    elif stock_filter == 'sold':
        games = games.filter(is_sold=True)
    
    # Sorting
    sort_by = request.GET.get('sort', '-created_at')
    if sort_by in ['name', '-name', 'final_price', '-final_price', 'created_at', '-created_at']:
        games = games.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(games, 12)  # 12 games per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'condition': condition,
        'stock_filter': stock_filter,
        'sort_by': sort_by,
        'condition_choices': BoardGame.CONDITION_CHOICES,
    }
    
    return render(request, 'catalog/catalog_list.html', context)


def game_detail(request, pk):
    """View detailed information about a board game"""
    game = get_object_or_404(BoardGame, pk=pk)
    images = game.get_images_list()
    
    context = {
        'game': game,
        'images': images,
    }
    
    return render(request, 'catalog/game_detail.html', context)


@ensure_csrf_cookie
def bgg_search(request):
    """Search Board Game Atlas API for board games"""
    # Explicitly force CSRF token generation and save to session
    csrf_token = get_token(request)
    
    # Ensure session is created and saved
    if not request.session.session_key:
        request.session.create()
    request.session.modified = True
    
    logger.info(f"=== BGA SEARCH DEBUG ===")
    logger.info(f"Method: {request.method}")
    logger.info(f"Session Key: {request.session.session_key}")
    
    if request.method == 'GET':
        # Force session save
        request.session.save()
        
        response = render(request, 'catalog/bgg_search.html')
        
        # Explicitly set session cookie if not present
        if 'sessionid' not in request.COOKIES and request.session.session_key:
            response.set_cookie(
                'sessionid',
                request.session.session_key,
                max_age=1209600,  # 2 weeks
                path='/',
                domain=None,
                httponly=False,
                samesite='Lax',
                secure=False
            )
        
        # Explicitly set CSRF cookie if not present
        if 'csrftoken' not in request.COOKIES:
            response.set_cookie(
                'csrftoken',
                csrf_token,
                max_age=31449600,  # 1 year
                path='/',
                domain=None,
                httponly=False,
                samesite='Lax',
                secure=False
            )
        
        return response
    
    elif request.method == 'POST':
        logger.info(f"=== POST REQUEST RECEIVED ===")
        logger.info(f"POST data: {request.POST}")
        
        query = request.POST.get('query', '').strip()
        
        if not query:
            messages.error(request, 'Please enter a search term')
            return render(request, 'catalog/bgg_search.html')
        
        # Search BoardGameGeek
        results = search_bgg_games(query)
        
        if results:
            messages.success(request, f'Found {len(results)} games matching "{query}"')
        else:
            messages.info(request, f'No games found for "{query}"')
        
        context = {
            'query': query,
            'results': results,
        }
        
        return render(request, 'catalog/bgg_search.html', context)


@ensure_csrf_cookie
def bgg_import(request, bgg_id):
    """Import a game from BoardGameGeek with prices from multiple sources and show form to add to catalog"""
    # Fetch game details from BoardGameGeek
    game_data = get_bgg_game_details(bgg_id)
    
    # If API fails, show error
    if not game_data or 'error' in game_data:
        messages.error(request, f'Could not find game with ID: {bgg_id}')
        return redirect('bgg_search')
    
    # Fetch prices from multiple sources
    from catalog.price_sources import PriceSourceService
    price_service = PriceSourceService(sitename="https://bgcatalog.fly.dev")
    offers = price_service.fetch_all_prices(int(bgg_id), game_data.get('name', ''))
    
    # Convert Offer objects to dictionaries for template compatibility
    price_sources = []
    for offer in offers:
        price_sources.append({
            'source': offer.source,
            'source_url': offer.source_url,
            'store_name': offer.store_name,
            'store_url': offer.store_url,
            'price_eur': offer.price_eur,
            'price_original': offer.price_original,
            'currency_original': offer.currency_original,
            'stock_status': offer.stock_status,
            'last_updated': offer.last_updated,
            'shipping_to_ie': offer.shipping_to_ie,
            'game_name': offer.game_name,
            'game_year': offer.game_year,
            'notes': offer.notes,
        })
    
    # Add price sources to game data
    game_data['price_sources'] = price_sources
    
    # Use lowest price as default if available
    if price_sources:
        game_data['msrp_price'] = price_sources[0].get('price_eur')
    
    if request.method == 'POST':
        # Process form submission
        try:
            # Create new game
            game = BoardGame()
            
            # BoardGameGeek data
            if bgg_id and bgg_id.isdigit():
                game.bgg_id = int(bgg_id)
            
            game.name = game_data['name']
            game.description = game_data.get('description', '')
            game.year_published = game_data.get('year_published')
            game.designer = game_data.get('designer', '')
            game.min_players = game_data.get('min_players')
            game.max_players = game_data.get('max_players')
            game.min_playtime = game_data.get('min_playtime')
            game.max_playtime = game_data.get('max_playtime')
            game.min_age = game_data.get('min_age')
            game.thumbnail_url = game_data.get('thumbnail_url', '')
            
            # Store images as JSON
            if game_data.get('image_url'):
                game.set_images_list([game_data['image_url']])
            
            # User inputs
            game.condition = request.POST.get('condition', 'new')
            game.stock_quantity = int(request.POST.get('stock_quantity', 1))
            game.notes = request.POST.get('notes', '')
            
            # Pricing - use BoardGamePrices data
            msrp_price = request.POST.get('msrp_price', '').strip()
            if not msrp_price and game_data.get('msrp_price'):
                msrp_price = str(game_data['msrp_price'])
            
            if msrp_price:
                game.msrp_price = Decimal(msrp_price)
            
            discount_percentage = request.POST.get('discount_percentage', '').strip()
            if discount_percentage:
                game.discount_percentage = Decimal(discount_percentage)
            
            game.save()
            
            # Sync to Google Sheets
            try:
                sheets = GoogleSheetsService()
                if sheets.authenticate() and sheets.get_or_create_spreadsheet():
                    sheets.sync_game_to_sheet(game)
            except:
                pass  # Don't fail if sheets sync fails
            
            messages.success(request, f'Successfully added "{game.name}" to catalog!')
            return redirect('game_detail', pk=game.pk)
        
        except Exception as e:
            messages.error(request, f'Error adding game: {str(e)}')
    
    # GET request - show form with BGG data pre-filled
    context = {
        'game_data': game_data,
        'condition_choices': BoardGame.CONDITION_CHOICES,
    }
    
    return render(request, 'catalog/game_form.html', context)


def game_edit(request, pk):
    """Edit an existing board game"""
    game = get_object_or_404(BoardGame, pk=pk)
    
    if request.method == 'POST':
        try:
            # Update fields
            game.name = request.POST.get('name', game.name)
            game.designer = request.POST.get('designer', '')
            game.condition = request.POST.get('condition', 'new')
            game.stock_quantity = int(request.POST.get('stock_quantity', 1))
            game.notes = request.POST.get('notes', '')
            game.description = request.POST.get('description', '')
            
            # Pricing
            msrp_price = request.POST.get('msrp_price', '').strip()
            if msrp_price:
                game.msrp_price = Decimal(msrp_price)
            
            discount_percentage = request.POST.get('discount_percentage', '').strip()
            if discount_percentage:
                game.discount_percentage = Decimal(discount_percentage)
            
            # Year published
            year = request.POST.get('year_published', '').strip()
            if year:
                game.year_published = int(year)
            
            game.save()
            
            # Sync to Google Sheets
            try:
                sheets = GoogleSheetsService()
                if sheets.authenticate() and sheets.get_or_create_spreadsheet():
                    sheets.sync_game_to_sheet(game)
            except:
                pass
            
            messages.success(request, f'Successfully updated "{game.name}"')
            return redirect('game_detail', pk=game.pk)
        
        except Exception as e:
            messages.error(request, f'Error updating game: {str(e)}')
    
    # GET request
    context = {
        'game': game,
        'game_data': {
            'name': game.name,
            'bgg_id': game.bgg_id,
            'description': game.description,
            'year_published': game.year_published,
            'designer': game.designer,
            'min_players': game.min_players,
            'max_players': game.max_players,
            'min_playtime': game.min_playtime,
            'max_playtime': game.max_playtime,
            'min_age': game.min_age,
            'thumbnail_url': game.thumbnail_url,
            'images': game.get_images_list(),
        },
        'condition_choices': BoardGame.CONDITION_CHOICES,
        'is_edit': True,
    }
    
    return render(request, 'catalog/game_form.html', context)


def game_create_manual(request):
    """Create a new board game manually (without BGG)"""
    if request.method == 'POST':
        try:
            # Create new game
            game = BoardGame()
            
            # Basic info
            game.name = request.POST.get('name', '').strip()
            game.description = request.POST.get('description', '').strip()
            game.designer = request.POST.get('designer', '').strip()
            
            # Game details
            year = request.POST.get('year_published', '').strip()
            if year:
                game.year_published = int(year)
            
            min_players = request.POST.get('min_players', '').strip()
            if min_players:
                game.min_players = int(min_players)
            
            max_players = request.POST.get('max_players', '').strip()
            if max_players:
                game.max_players = int(max_players)
            
            min_playtime = request.POST.get('min_playtime', '').strip()
            if min_playtime:
                game.min_playtime = int(min_playtime)
            
            max_playtime = request.POST.get('max_playtime', '').strip()
            if max_playtime:
                game.max_playtime = int(max_playtime)
            
            min_age = request.POST.get('min_age', '').strip()
            if min_age:
                game.min_age = int(min_age)
            
            # Condition and stock
            game.condition = request.POST.get('condition', 'new')
            game.stock_quantity = int(request.POST.get('stock_quantity', 1))
            game.notes = request.POST.get('notes', '').strip()
            
            # Pricing
            msrp_price = request.POST.get('msrp_price', '').strip()
            if msrp_price:
                game.msrp_price = Decimal(msrp_price)
            
            discount_percentage = request.POST.get('discount_percentage', '').strip()
            if discount_percentage:
                game.discount_percentage = Decimal(discount_percentage)
            
            # Image URL
            thumbnail_url = request.POST.get('thumbnail_url', '').strip()
            if thumbnail_url:
                game.thumbnail_url = thumbnail_url
                game.set_images_list([thumbnail_url])
            
            game.save()
            
            # Sync to Google Sheets
            try:
                sheets = GoogleSheetsService()
                if sheets.authenticate() and sheets.get_or_create_spreadsheet():
                    sheets.sync_game_to_sheet(game)
            except:
                pass  # Don't fail if sheets sync fails
            
            messages.success(request, f'Successfully added "{game.name}" to catalog!')
            return redirect('game_detail', pk=game.pk)
        
        except Exception as e:
            messages.error(request, f'Error adding game: {str(e)}')
    
    # GET request - show empty form
    context = {
        'game_data': None,
        'condition_choices': BoardGame.CONDITION_CHOICES,
        'is_manual': True,
    }
    
    return render(request, 'catalog/game_form.html', context)


def game_delete(request, pk):
    """Delete a board game"""
    game = get_object_or_404(BoardGame, pk=pk)
    
    if request.method == 'POST':
        game_name = game.name
        game_id = game.id
        
        # Delete from Google Sheets
        try:
            sheets = GoogleSheetsService()
            if sheets.authenticate() and sheets.get_or_create_spreadsheet():
                sheets.delete_game_from_sheet(game_id)
        except:
            pass
        
        game.delete()
        messages.success(request, f'Successfully deleted "{game_name}"')
        return redirect('catalog_list')
    
    context = {
        'game': game,
    }
    
    return render(request, 'catalog/game_confirm_delete.html', context)


def game_mark_sold(request, pk):
    """Mark a game as sold"""
    game = get_object_or_404(BoardGame, pk=pk)
    
    if request.method == 'POST':
        game.is_sold = True
        game.save()
        
        # Sync to Google Sheets
        try:
            sheets = GoogleSheetsService()
            if sheets.authenticate() and sheets.get_or_create_spreadsheet():
                sheets.sync_game_to_sheet(game)
        except:
            pass
        
        messages.success(request, f'Marked "{game.name}" as sold')
        return redirect('game_detail', pk=game.pk)
    
    return redirect('game_detail', pk=game.pk)


def game_unmark_sold(request, pk):
    """Unmark a game as sold"""
    game = get_object_or_404(BoardGame, pk=pk)
    
    if request.method == 'POST':
        game.is_sold = False
        game.stock_quantity = int(request.POST.get('stock_quantity', 1))
        game.save()
        
        # Sync to Google Sheets
        try:
            sheets = GoogleSheetsService()
            if sheets.authenticate() and sheets.get_or_create_spreadsheet():
                sheets.sync_game_to_sheet(game)
        except:
            pass
        
        messages.success(request, f'Unmarked "{game.name}" as sold')
        return redirect('game_detail', pk=game.pk)
    
    return redirect('game_detail', pk=game.pk)


def public_catalog(request):
    """Public-facing catalog for customers"""
    games = BoardGame.objects.filter(is_sold=False, stock_quantity__gt=0)
    
    # Search filter
    search_query = request.GET.get('search', '')
    if search_query:
        games = games.filter(
            Q(name__icontains=search_query) |
            Q(designer__icontains=search_query)
        )
    
    # Sorting
    sort_by = request.GET.get('sort', 'name')
    if sort_by in ['name', '-name', 'final_price', '-final_price', '-created_at']:
        games = games.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(games, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'sort_by': sort_by,
    }
    
    return render(request, 'catalog/public_catalog.html', context)


def public_game_detail(request, pk):
    """Public-facing game detail for customers"""
    game = get_object_or_404(BoardGame, pk=pk, is_sold=False, stock_quantity__gt=0)
    images = game.get_images_list()
    
    context = {
        'game': game,
        'images': images,
    }
    
    return render(request, 'catalog/public_game_detail.html', context)


def sync_to_sheets(request):
    """Manual sync all games to Google Sheets"""
    if request.method == 'POST':
        try:
            sheets = GoogleSheetsService()
            if sheets.authenticate() and sheets.get_or_create_spreadsheet():
                games = BoardGame.objects.all()
                if sheets.sync_all_games(games):
                    messages.success(request, 'Successfully synced all games to Google Sheets')
                else:
                    messages.error(request, 'Failed to sync to Google Sheets')
            else:
                messages.error(request, 'Failed to authenticate with Google Sheets')
        except Exception as e:
            messages.error(request, f'Error syncing to Google Sheets: {str(e)}')
        
        return redirect('catalog_list')
    
    return redirect('catalog_list')
