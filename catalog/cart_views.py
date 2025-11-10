"""
Shopping cart and checkout views.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import BoardGame, StockReservation


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
    cart_items = []
    total = 0
    
    for game_id, quantity in cart.items():
        try:
            game = BoardGame.objects.get(id=game_id)
            item_total = game.final_price * quantity if game.final_price else 0
            total += item_total
            
            cart_items.append({
                'game': game,
                'quantity': quantity,
                'item_total': item_total,
            })
        except BoardGame.DoesNotExist:
            # Remove invalid items
            pass
    
    context = {
        'cart_items': cart_items,
        'total': total,
    }
    
    return render(request, 'catalog/cart.html', context)


def add_to_cart(request, game_id):
    """Add game to cart."""
    game = get_object_or_404(BoardGame, id=game_id)
    
    if game.is_sold or game.available_quantity <= 0:
        messages.error(request, 'This game is not available')
        return redirect('game_detail', game_id=game_id)
    
    cart = get_cart(request)
    game_id_str = str(game_id)
    
    # Get requested quantity
    quantity = int(request.POST.get('quantity', 1))
    
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
    
    quantity = int(request.POST.get('quantity', 0))
    
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


def checkout(request):
    """Checkout and create reservations."""
    if request.method != 'POST':
        return redirect('view_cart')
    
    cart = get_cart(request)
    
    if not cart:
        messages.error(request, 'Your cart is empty')
        return redirect('view_cart')
    
    # Get customer information
    customer_name = request.POST.get('customer_name', '')
    customer_email = request.POST.get('customer_email', '')
    customer_phone = request.POST.get('customer_phone', '')
    
    if not customer_name or not customer_email:
        messages.error(request, 'Please provide your name and email')
        return redirect('view_cart')
    
    # Create session key if needed
    if not request.session.session_key:
        request.session.create()
    
    session_key = request.session.session_key
    
    # Create reservations atomically
    try:
        with transaction.atomic():
            reservations = []
            
            for game_id, quantity in cart.items():
                game = BoardGame.objects.select_for_update().get(id=game_id)
                
                # Validate stock
                if quantity > game.available_quantity:
                    raise ValueError(f'Insufficient stock for {game.name}')
                
                # Create reservation
                reservation = StockReservation.objects.create(
                    game=game,
                    quantity=quantity,
                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone,
                    session_key=session_key,
                )
                reservations.append(reservation)
            
            # Clear cart
            request.session['cart'] = {}
            request.session.modified = True
            
            # Send quote email
            _send_quote_email(customer_email, customer_name, reservations)
            
            messages.success(request, 'Quote request sent! Stock reserved for 30 minutes.')
            return redirect('checkout_success')
    
    except ValueError as e:
        messages.error(request, str(e))
        return redirect('view_cart')
    except Exception as e:
        messages.error(request, f'Checkout failed: {str(e)}')
        return redirect('view_cart')


def checkout_success(request):
    """Display checkout success page."""
    return render(request, 'catalog/checkout_success.html')


def _send_quote_email(customer_email, customer_name, reservations):
    """Send quote email to customer."""
    total = sum(r.game.final_price * r.quantity for r in reservations if r.game.final_price)
    
    items_text = '\n'.join([
        f"- {r.game.name} x {r.quantity} @ €{r.game.final_price} = €{r.game.final_price * r.quantity}"
        for r in reservations
    ])
    
    message = f"""
    Dear {customer_name},
    
    Thank you for your interest in our board games!
    
    Here is your quote:
    
    {items_text}
    
    Total: €{total:.2f}
    
    Your items are reserved for 30 minutes. We will contact you shortly to complete the purchase.
    
    Best regards,
    BG Catalog Team
    """
    
    try:
        send_mail(
            subject='Your Board Game Quote',
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer_email],
            fail_silently=False,
        )
    except Exception as e:
        # Log error but don't fail checkout
        print(f"Failed to send email: {e}")
