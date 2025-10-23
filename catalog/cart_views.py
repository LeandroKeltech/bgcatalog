"""
Views para carrinho de compras e área administrativa
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Sum, Q
from .models import BoardGame, CartItem, StockReservation


def get_or_create_session_key(request):
    """Get or create session key for cart"""
    if not request.session.session_key:
        request.session.create()
    return request.session.session_key


def cart_view(request):
    """View shopping cart"""
    session_key = get_or_create_session_key(request)
    cart_items = CartItem.objects.filter(session_key=session_key)
    
    total = sum(item.subtotal for item in cart_items)
    
    context = {
        'cart_items': cart_items,
        'total': total,
    }
    
    return render(request, 'catalog/cart.html', context)


def add_to_cart(request, pk):
    """Add game to shopping cart"""
    game = get_object_or_404(BoardGame, pk=pk)
    
    if not game.is_available:
        messages.error(request, 'This game is not available at the moment.')
        return redirect('public_catalog')
    
    session_key = get_or_create_session_key(request)
    
    cart_item, created = CartItem.objects.get_or_create(
        session_key=session_key,
        game=game,
        defaults={'quantity': 1}
    )
    
    if not created:
        available = game.available_quantity
        if cart_item.quantity < available:
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, f'Quantity of "{game.name}" updated in cart!')
        else:
            messages.warning(request, f'Maximum available quantity of "{game.name}" is already in cart.')
    else:
        messages.success(request, f'"{game.name}" added to cart!')
    
    return redirect('cart_view')


def remove_from_cart(request, pk):
    """Remove item from cart"""
    session_key = get_or_create_session_key(request)
    cart_item = get_object_or_404(CartItem, pk=pk, session_key=session_key)
    
    game_name = cart_item.game.name
    cart_item.delete()
    
    messages.success(request, f'"{game_name}" removed from cart.')
    return redirect('cart_view')


def update_cart_quantity(request, pk):
    """Update cart item quantity"""
    if request.method == 'POST':
        session_key = get_or_create_session_key(request)
        cart_item = get_object_or_404(CartItem, pk=pk, session_key=session_key)
        
        try:
            quantity = int(request.POST.get('quantity', 1))
            available = cart_item.game.available_quantity
            if quantity > 0 and quantity <= available:
                cart_item.quantity = quantity
                cart_item.save()
                messages.success(request, 'Quantity updated!')
            else:
                messages.error(request, f'Invalid quantity. Maximum available: {available}')
        except ValueError:
            messages.error(request, 'Invalid quantity.')
    
    return redirect('cart_view')


def send_cart_email(request):
    """Send cart contents to admin email and create stock reservations"""
    if request.method == 'POST':
        session_key = get_or_create_session_key(request)
        cart_items = CartItem.objects.filter(session_key=session_key)
        
        if not cart_items.exists():
            messages.error(request, 'Your cart is empty.')
            return redirect('cart_view')
        
        # Get customer info
        customer_name = request.POST.get('customer_name', 'Customer')
        customer_email = request.POST.get('customer_email', '')
        customer_phone = request.POST.get('customer_phone', '')
        customer_message = request.POST.get('message', '')
        
        # Check availability and create reservations first
        reservations_created = []
        availability_errors = []
        
        for item in cart_items:
            available = item.game.available_quantity
            if item.quantity > available:
                availability_errors.append(
                    f"{item.game.name}: requested {item.quantity}, only {available} available"
                )
            else:
                # Create reservation
                try:
                    reservation = StockReservation.objects.create(
                        game=item.game,
                        quantity=item.quantity,
                        customer_name=customer_name,
                        customer_email=customer_email,
                        customer_phone=customer_phone,
                        customer_message=customer_message,
                        session_key=session_key,
                    )
                    reservations_created.append(reservation)
                except Exception as e:
                    availability_errors.append(f"{item.game.name}: reservation failed - {str(e)}")
        
        # If there are availability errors, cancel all reservations and show error
        if availability_errors:
            for reservation in reservations_created:
                reservation.delete()
            
            error_message = "Some items are no longer available:\n" + "\n".join(availability_errors)
            messages.error(request, error_message)
            return redirect('cart_view')
        
        # Build email message
        total = sum(item.subtotal for item in cart_items)
        
        message_body = f"""
New Quote Request from Board Game Catalog Website
========================================================

CUSTOMER INFORMATION:
Name: {customer_name}
Email: {customer_email}
Phone: {customer_phone}

CUSTOMER MESSAGE:
{customer_message}

REQUESTED ITEMS:
{'='*60}

"""
        
        for item in cart_items:
            game = item.game
            message_body += f"""
Game: {game.name}
Quantity: {item.quantity}
Unit Price: €{game.final_price:.2f}
Subtotal: €{item.subtotal:.2f}
Condition: {game.get_condition_display()}
Stock Available: {game.stock_quantity}
---
"""
        
        message_body += f"""
{'='*60}
TOTAL: €{total:.2f}
{'='*60}

*** STOCK RESERVED ***
Items have been temporarily reserved for 30 minutes.
Please confirm or cancel the sale in the admin panel.

Reservation IDs: {', '.join([str(r.id) for r in reservations_created])}

This is a quote request. Please contact the customer to confirm the purchase.
"""
        
        try:
            print(f"Attempting to send email...")
            print(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
            print(f"EMAIL_HOST: {getattr(settings, 'EMAIL_HOST', 'Not set')}")
            print(f"EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', 'Not set')}")
            print(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
            print(f"ADMIN_EMAIL: {settings.ADMIN_EMAIL}")
            
            send_mail(
                subject=f'New Quote Request - {customer_name} [STOCK RESERVED]',
                message=message_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=False,
            )
            
            print("Email sent successfully!")
            print(f"Created {len(reservations_created)} stock reservations")
            
            # Clear cart after sending email and creating reservations
            cart_items.delete()
            
            messages.success(request, 
                f'Your request was sent successfully! '
                f'We have reserved {len(reservations_created)} item(s) for 30 minutes. '
                f'We will contact you soon to confirm your purchase.'
            )
            return redirect('public_catalog')
            
        except Exception as e:
            print(f"Email sending failed: {str(e)}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
            
            # If email fails, cancel reservations
            for reservation in reservations_created:
                reservation.delete()
            
            messages.error(request, f'Error sending request: {str(e)}. Please try again.')
            return redirect('cart_view')
    
    return redirect('cart_view')


# Admin Panel Views

def admin_login(request):
    """Admin login page"""
    if request.user.is_authenticated:
        return redirect('admin_panel')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            return redirect('admin_panel')
        else:
            messages.error(request, 'Incorrect username or password.')
    
    return render(request, 'catalog/admin_login.html')


def admin_logout(request):
    """Admin logout"""
    auth_logout(request)
    messages.success(request, 'You have logged out of the admin area.')
    return redirect('public_catalog')


@login_required
def admin_panel(request):
    """Admin panel - catalog management"""
    games = BoardGame.objects.all()
    
    # Search filter
    search_query = request.GET.get('search', '')
    if search_query:
        games = games.filter(
            Q(name__icontains=search_query) |
            Q(designer__icontains=search_query)
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
    if sort_by:
        games = games.order_by(sort_by)
    
    # Get active reservations
    active_reservations = StockReservation.objects.filter(status='active').order_by('-created_at')
    
    # Statistics
    stats = {
        'total_games': BoardGame.objects.count(),
        'in_stock': BoardGame.objects.filter(stock_quantity__gt=0, is_sold=False).count(),
        'sold': BoardGame.objects.filter(is_sold=True).count(),
        'total_value': BoardGame.objects.filter(is_sold=False).aggregate(
            total=Sum('final_price')
        )['total'] or 0,
        'active_reservations': active_reservations.count(),
        'reserved_items': sum(r.quantity for r in active_reservations),
    }
    
    context = {
        'games': games,
        'search_query': search_query,
        'condition_choices': BoardGame.CONDITION_CHOICES,
        'sort_by': sort_by,
        'stats': stats,
        'active_reservations': active_reservations,
    }
    
    return render(request, 'catalog/admin_panel.html', context)


@login_required
def reservation_management(request):
    """Manage stock reservations"""
    # Cleanup expired reservations first
    expired_count = StockReservation.cleanup_expired()
    if expired_count > 0:
        messages.info(request, f'Cleaned up {expired_count} expired reservations.')
    
    reservations = StockReservation.objects.all().order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        reservations = reservations.filter(status=status_filter)
    
    context = {
        'reservations': reservations,
        'status_filter': status_filter,
        'status_choices': StockReservation.STATUS_CHOICES,
    }
    
    return render(request, 'catalog/reservation_management.html', context)


@login_required
def confirm_reservation(request, pk):
    """Confirm a reservation and complete the sale"""
    reservation = get_object_or_404(StockReservation, pk=pk)
    
    if request.method == 'POST':
        admin_notes = request.POST.get('admin_notes', '')
        
        try:
            reservation.confirm_sale(admin_notes)
            messages.success(request, 
                f'Sale confirmed for {reservation.game.name} x{reservation.quantity}. '
                f'Stock reduced from {reservation.game.stock_quantity + reservation.quantity} '
                f'to {reservation.game.stock_quantity}.'
            )
        except ValueError as e:
            messages.error(request, f'Cannot confirm sale: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error confirming sale: {str(e)}')
    
    return redirect('reservation_management')


@login_required
def cancel_reservation(request, pk):
    """Cancel a reservation"""
    reservation = get_object_or_404(StockReservation, pk=pk)
    
    if request.method == 'POST':
        admin_notes = request.POST.get('admin_notes', '')
        
        try:
            reservation.cancel_reservation(admin_notes)
            messages.success(request, f'Reservation cancelled for {reservation.game.name} x{reservation.quantity}.')
        except ValueError as e:
            messages.error(request, f'Cannot cancel reservation: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error cancelling reservation: {str(e)}')
    
    return redirect('reservation_management')


@login_required
def extend_reservation(request, pk):
    """Extend a reservation time"""
    reservation = get_object_or_404(StockReservation, pk=pk)
    
    if request.method == 'POST':
        try:
            minutes = int(request.POST.get('minutes', 30))
            reservation.extend_reservation(minutes)
            messages.success(request, f'Reservation extended by {minutes} minutes.')
        except ValueError as e:
            messages.error(request, f'Cannot extend reservation: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error extending reservation: {str(e)}')
    
    return redirect('reservation_management')
