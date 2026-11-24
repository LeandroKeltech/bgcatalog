"""
Admin panel views - CRUD operations for board games and inventory management.
"""

from django.shortcuts import render, redirect, get_object_or_404
from .access import admin_group_required
from django.contrib import messages
from django.db import transaction
from django.db.models import Q, Sum
from django.core.paginator import Paginator
from django.db.models.deletion import ProtectedError
from .forms import InventoryForm
from .finance import confirm_reserved_sale
from .models import BoardGame, StockReservation


@admin_group_required
def admin_panel(request):
    """Main admin panel - list all games."""
    games = BoardGame.objects.all().order_by('name', 'id')
    availability = request.GET.get('availability', 'all')
    if availability == 'available':
        games = games.filter(is_sold=False, stock_quantity__gt=0)
    elif availability == 'sold_out':
        games = games.filter(Q(is_sold=True) | Q(stock_quantity=0))
    
    search_query = request.GET.get('search', '')
    if search_query:
        games = games.filter(name__icontains=search_query)

    condition = request.GET.get('condition', 'all')
    if condition == 'not_new':
        games = games.exclude(condition='new')
    elif condition in dict(BoardGame.CONDITION_CHOICES):
        games = games.filter(condition=condition)
    else:
        condition = 'all'

    per_page = request.GET.get('per_page', '50')
    if per_page not in ('25', '50', '100'):
        per_page = '50'
    page = Paginator(games, int(per_page)).get_page(request.GET.get('page'))
    context = {
        'games': page.object_list,
        'page_obj': page,
        'search_query': search_query,
        'availability': availability,
        'per_page': per_page,
        'condition': condition,
        'condition_choices': BoardGame.CONDITION_CHOICES,
        'total_games': BoardGame.objects.count(),
        'stock_units': BoardGame.objects.aggregate(total=Sum('stock_quantity'))['total'] or 0,
        'sold_out_count': BoardGame.objects.filter(Q(is_sold=True) | Q(stock_quantity=0)).count(),
    }
    
    return render(request, 'catalog/inventory_dashboard.html', context)


@admin_group_required
def edit_game(request, game_id):
    """Edit existing game."""
    with transaction.atomic():
        game = get_object_or_404(BoardGame.objects.select_for_update(), id=game_id)
        form = InventoryForm(request.POST or None, instance=game)
        if request.method == 'POST' and form.is_valid():
            form.save()
            messages.success(request, f'Inventory updated for {game.name}.')
            return redirect('admin_panel')
    return render(request, 'catalog/inventory_edit.html', {'form': form, 'game': game})


@admin_group_required
def new_game(request):
    form = InventoryForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        game = form.save()
        messages.success(request, f'{game.name} added to the inventory.')
        return redirect('admin_panel')
    return render(request, 'catalog/inventory_edit.html', {'form': form})


@admin_group_required
def delete_game(request, game_id):
    """Delete game from catalog."""
    game = get_object_or_404(BoardGame, id=game_id)
    
    if request.method == 'POST':
        game_name = game.name
        try:
            game.delete()
        except ProtectedError:
            messages.error(request, 'This game has sales or reservation history. Set its stock to zero instead of deleting it.')
            return redirect('admin_panel')
        messages.success(request, f'Game "{game_name}" deleted successfully!')
        return redirect('admin_panel')
    
    context = {'game': game}
    return render(request, 'catalog/delete_game.html', context)


@admin_group_required
def reservation_management(request):
    """Manage stock reservations."""
    # Expire old reservations first
    StockReservation.expire_old_reservations()
    
    # Get all reservations
    reservations = StockReservation.objects.all().select_related('game')
    
    # Filter by status
    status = request.GET.get('status', 'active')
    if status:
        reservations = reservations.filter(status=status)

    quote_id = request.GET.get('quote', '')
    if quote_id:
        from uuid import UUID
        try:
            reservations = reservations.filter(customer_quote_id=UUID(quote_id))
        except ValueError:
            reservations = reservations.none()
    
    context = {
        'reservations': reservations,
        'status': status,
        'status_choices': StockReservation.STATUS_CHOICES,
        'quote_id': quote_id,
    }
    
    return render(request, 'catalog/reservation_management.html', context)


@admin_group_required
def confirm_reservation(request, reservation_id):
    """Confirm reservation and complete sale."""
    reservation = get_object_or_404(StockReservation, id=reservation_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                sale = confirm_reserved_sale(reservation.pk, actor=request.user)
                messages.success(request, 'Sale confirmed and stock updated. Promotion bundles are confirmed together; record payments against the linked sales when received.')
                return redirect('sale_detail', sale_id=sale.pk)
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('reservation_management')
    
    context = {'reservation': reservation}
    return render(request, 'catalog/confirm_reservation.html', context)


@admin_group_required
def cancel_reservation(request, reservation_id):
    """Cancel reservation and release stock."""
    reservation = get_object_or_404(StockReservation, id=reservation_id)
    
    if request.method == 'POST':
        try:
            reservation.cancel()
            messages.success(request, 'Reservation cancelled successfully!')
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('reservation_management')
    
    context = {'reservation': reservation}
    return render(request, 'catalog/cancel_reservation.html', context)


@admin_group_required
def extend_reservation(request, reservation_id):
    """Extend reservation expiry time."""
    reservation = get_object_or_404(StockReservation, id=reservation_id)
    
    if request.method == 'POST':
        try:
            minutes = int(request.POST.get('minutes', 30))
            reservation.extend(minutes=minutes)
            messages.success(request, f'Reservation extended by {minutes} minutes!')
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('reservation_management')
    
    context = {'reservation': reservation}
    return render(request, 'catalog/extend_reservation.html', context)
