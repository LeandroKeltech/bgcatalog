"""
Admin panel views - CRUD operations for board games and inventory management.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db import transaction
from .models import BoardGame, StockReservation


@staff_member_required
def admin_panel(request):
    """Main admin panel - list all games."""
    games = BoardGame.objects.all().order_by('-created_at')
    
    # Filter options
    show_sold = request.GET.get('show_sold', '')
    if not show_sold:
        games = games.filter(is_sold=False)
    
    search_query = request.GET.get('search', '')
    if search_query:
        games = games.filter(name__icontains=search_query)
    
    context = {
        'games': games,
        'search_query': search_query,
        'show_sold': show_sold,
    }
    
    return render(request, 'catalog/admin_panel.html', context)


@staff_member_required
def edit_game(request, game_id):
    """Edit existing game."""
    game = get_object_or_404(BoardGame, id=game_id)
    
    if request.method == 'POST':
        # Update game fields
        game.name = request.POST.get('name', game.name)
        game.designer = request.POST.get('designer', game.designer)
        game.year_published = request.POST.get('year_published') or None
        game.description = request.POST.get('description', game.description)
        game.stock_quantity = int(request.POST.get('stock_quantity', 1))
        game.condition = request.POST.get('condition', 'new')
        game.msrp_price = request.POST.get('msrp_price') or None
        game.discount_percentage = int(request.POST.get('discount_percentage', 0))
        game.notes = request.POST.get('notes', '')
        game.is_sold = request.POST.get('is_sold') == 'on'
        
        # Update gameplay details
        game.min_players = request.POST.get('min_players') or None
        game.max_players = request.POST.get('max_players') or None
        game.min_playtime = request.POST.get('min_playtime') or None
        game.max_playtime = request.POST.get('max_playtime') or None
        game.min_age = request.POST.get('min_age') or None
        
        game.save()
        messages.success(request, f'Game "{game.name}" updated successfully!')
        return redirect('admin_panel')
    
    context = {
        'game': game,
        'condition_choices': BoardGame.CONDITION_CHOICES,
    }
    
    return render(request, 'catalog/edit_game.html', context)


@staff_member_required
def delete_game(request, game_id):
    """Delete game from catalog."""
    game = get_object_or_404(BoardGame, id=game_id)
    
    if request.method == 'POST':
        game_name = game.name
        game.delete()
        messages.success(request, f'Game "{game_name}" deleted successfully!')
        return redirect('admin_panel')
    
    context = {'game': game}
    return render(request, 'catalog/delete_game.html', context)


@staff_member_required
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
    
    context = {
        'reservations': reservations,
        'status': status,
        'status_choices': StockReservation.STATUS_CHOICES,
    }
    
    return render(request, 'catalog/reservation_management.html', context)


@staff_member_required
def confirm_reservation(request, reservation_id):
    """Confirm reservation and complete sale."""
    reservation = get_object_or_404(StockReservation, id=reservation_id)
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                reservation.confirm()
                messages.success(request, f'Reservation confirmed! Stock reduced by {reservation.quantity}.')
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('reservation_management')
    
    context = {'reservation': reservation}
    return render(request, 'catalog/confirm_reservation.html', context)


@staff_member_required
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


@staff_member_required
def extend_reservation(request, reservation_id):
    """Extend reservation expiry time."""
    reservation = get_object_or_404(StockReservation, id=reservation_id)
    
    if request.method == 'POST':
        minutes = int(request.POST.get('minutes', 30))
        try:
            reservation.extend(minutes=minutes)
            messages.success(request, f'Reservation extended by {minutes} minutes!')
        except ValueError as e:
            messages.error(request, str(e))
        
        return redirect('reservation_management')
    
    context = {'reservation': reservation}
    return render(request, 'catalog/extend_reservation.html', context)
