"""
Shopping cart and checkout views.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils import timezone
from django.views.decorators.http import require_POST
from datetime import timedelta
from uuid import uuid4
from django.conf import settings
from django.contrib.auth import get_user_model
from .cart_pricing import price_cart
from .models import BoardGame, StockReservation, CustomerProfile, CustomerQuote
from .notifications import create_reservation_notification
from .whatsapp import shop_whatsapp_number


def get_cart(request):
    """Get cart from session."""
    return request.session.get('cart', {})


def save_cart(request, cart):
    """Save cart to session."""
    request.session['cart'] = cart
    request.session.modified = True


def view_cart(request):
    """Display shopping cart."""
    cart = get_cart(request)
    try:
        context = price_cart(cart, BoardGame.objects.in_bulk(cart.keys()))
    except (ValueError, TypeError):
        messages.error(request, 'This cart contains invalid items. Please add your games again.')
        save_cart(request, {})
        context = {'cart_items': []}
    
    context['customer_profile'] = CustomerProfile.objects.filter(user=request.user).first() if request.user.is_authenticated else None
    return render(request, 'catalog/cart.html', context)


@require_POST
def add_to_cart(request, game_id):
    """Add game to cart."""
    game = get_object_or_404(BoardGame, id=game_id)
    
    if game.is_sold or game.available_quantity <= 0:
        messages.error(request, 'This game is not available')
        return redirect('game_detail', game_id=game_id)
    
    cart = get_cart(request)
    game_id_str = str(game_id)
    
    # Get requested quantity
    try:
        quantity = int(request.POST.get('quantity', 1))
        if not 1 <= quantity <= 10000:
            raise ValueError
    except (TypeError, ValueError):
        messages.error(request, 'Enter a whole quantity between 1 and 10000.')
        return redirect('game_detail', game_id=game_id)
    
    # Check stock availability
    current_cart_qty = cart.get(game_id_str, 0)
    new_total = current_cart_qty + quantity
    
    if new_total > game.available_quantity:
        messages.error(request, f'Only {game.available_quantity} available in stock')
        return redirect('game_detail', game_id=game_id)
    
    # Update cart
    cart[game_id_str] = new_total
    save_cart(request, cart)
    
    messages.success(request, f'Added {quantity}x "{game.name}" to cart')
    return redirect('view_cart')


def update_cart(request, game_id):
    """Update cart quantity."""
    if request.method != 'POST':
        return redirect('view_cart')
    
    game = get_object_or_404(BoardGame, id=game_id)
    cart = get_cart(request)
    game_id_str = str(game_id)
    
    try:
        quantity = int(request.POST.get('quantity', 0))
        if not 0 <= quantity <= 10000:
            raise ValueError
    except (TypeError, ValueError):
        messages.error(request, 'Enter a whole quantity between 0 and 10000.')
        return redirect('view_cart')
    
    if quantity <= 0:
        # Remove from cart
        if game_id_str in cart:
            del cart[game_id_str]
        messages.info(request, f'Removed "{game.name}" from cart')
    else:
        # Check stock
        if quantity > game.available_quantity:
            messages.error(request, f'Only {game.available_quantity} available')
            return redirect('view_cart')
        
        cart[game_id_str] = quantity
        messages.success(request, f'Updated quantity for "{game.name}"')
    
    save_cart(request, cart)
    return redirect('view_cart')


@require_POST
def remove_from_cart(request, game_id):
    """Remove game from cart."""
    cart = get_cart(request)
    game_id_str = str(game_id)
    
    if game_id_str in cart:
        game = BoardGame.objects.get(id=game_id)
        del cart[game_id_str]
        save_cart(request, cart)
        messages.success(request, f'Removed "{game.name}" from cart')
    
    return redirect('view_cart')


@login_required(login_url='customer_login')
def checkout(request):
    """Checkout and create reservations."""
    if request.method != 'POST':
        return redirect('view_cart')
    
    cart = get_cart(request)
    
    if not cart:
        messages.error(request, 'Your cart is empty')
        return redirect('view_cart')
    
    profile = CustomerProfile.objects.filter(user=request.user).first()
    if not profile or not request.user.email or not profile.phone:
        messages.info(request, 'Complete your contact details before checkout.')
        return redirect('customer_account')
    try:
        shop_whatsapp_number()
    except ImproperlyConfigured:
        messages.error(request, 'WhatsApp checkout is temporarily unavailable. Please try again later.')
        return redirect('view_cart')
    
    # Create session key if needed
    if not request.session.session_key:
        request.session.create()
    
    session_key = request.session.session_key
    
    # Create reservations atomically
    try:
        with transaction.atomic():
            reservations = []
            # Serialize checkouts before counting active holds for this account.
            get_user_model().objects.select_for_update().get(pk=request.user.pk)
            active_quotes = CustomerQuote.objects.filter(
                user=request.user, reservations__status='active',
                reservations__expires_at__gt=timezone.now(),
            ).distinct().count()
            if active_quotes >= settings.MAX_ACTIVE_CUSTOMER_QUOTES:
                raise ValueError('You already have active reservations. Please complete them before reserving more games.')
            # Lock all games in stable order, then evaluate one consistent quote.
            games = {game.pk: game for game in BoardGame.objects.select_for_update().filter(pk__in=cart.keys()).order_by('pk')}
            quote = price_cart(cart, games)
            if not quote['can_checkout']:
                raise ValueError('Resolve unavailable stock or unconfirmed prices before checkout.')
            group_id = uuid4() if quote['applied_promotion'] else None
            promotion = quote['applied_promotion']
            snapshot = ({'id': promotion.pk, 'name': promotion.name, 'kind': promotion.kind,
                         'rule': promotion.mechanic_description, 'subtotal': str(quote['subtotal']),
                         'discount': str(quote['discount']), 'total': str(quote['total'])} if promotion else {})
            expires_at = timezone.now() + timedelta(minutes=30)
            saved_quote = CustomerQuote.objects.create(user=request.user, expires_at=expires_at, snapshot={
                'contact': {'full_name': profile.full_name, 'email': request.user.email, 'phone': profile.phone},
                'lines': [{'name': line['game'].name, 'condition': line['game'].get_condition_display(),
                           'quantity': line['quantity'], 'line_total': f"{line['item_total']:.2f}",
                           'price_groups': [{'unit_price': f'{price:.2f}', 'quantity': count}
                                            for price, count in line['price_groups']]}
                          for line in quote['cart_items']],
                'subtotal': f"{quote['subtotal']:.2f}", 'discount': f"{quote['discount']:.2f}",
                'total': f"{quote['total']:.2f}",
                'offer': promotion.name if promotion else ('Best product offers' if quote['discount'] else ''),
                'offer_rule': promotion.mechanic_description if promotion else '',
            })
            for line in quote['cart_items']:
                game, quantity = line['game'], line['quantity']
                if game.is_sold:
                    raise ValueError(f'{game.name} is sold out.')
                if game.final_price is None:
                    raise ValueError(f'Price unavailable for {game.name}. Please contact us before checkout.')
                
                # Validate stock
                if quantity > game.available_quantity:
                    raise ValueError(f'Insufficient stock for {game.name}')
                
                # Split a line only where unit prices differ (for example, a free copy).
                for unit_price, count in line['price_groups']:
                    reservation = StockReservation.objects.create(
                        game=game, quantity=count, quoted_unit_price=unit_price,
                        customer_quote=saved_quote,
                        quote_group=group_id, promotion_snapshot=snapshot,
                        customer_name=profile.full_name, customer_email=request.user.email,
                        customer_phone=profile.phone, session_key=session_key, expires_at=expires_at,
                    )
                    reservations.append(reservation)
            
            # The alert commits with the stock holds, even if WhatsApp is never opened.
            create_reservation_notification(saved_quote)

            # Clear cart
            request.session['cart'] = {}
            request.session['last_quote_id'] = str(saved_quote.pk)
            request.session.modified = True
            
            messages.success(request, 'Games reserved for 30 minutes. Open WhatsApp and press Send to contact the shop.')
            return redirect('checkout_success')
    
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('view_cart')
    except Exception:
        import logging
        logging.getLogger(__name__).exception('Checkout could not be completed')
        messages.error(request, 'Checkout could not be completed. Please try again.')
        return redirect('view_cart')


@login_required(login_url='customer_login')
def checkout_success(request):
    """Return to the authenticated customer's most recent saved quote."""
    quote_id = request.session.get('last_quote_id')
    if not quote_id:
        return redirect('view_cart')
    from .customer_views import customer_quote
    return customer_quote(request, quote_id=quote_id)
