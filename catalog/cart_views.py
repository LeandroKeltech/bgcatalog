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
from .models import BoardGame, CartItem


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
    
    if not game.in_stock:
        messages.error(request, 'This game is not available at the moment.')
        return redirect('public_catalog')
    
    session_key = get_or_create_session_key(request)
    
    cart_item, created = CartItem.objects.get_or_create(
        session_key=session_key,
        game=game,
        defaults={'quantity': 1}
    )
    
    if not created:
        if cart_item.quantity < game.stock_quantity:
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
            if quantity > 0 and quantity <= cart_item.game.stock_quantity:
                cart_item.quantity = quantity
                cart_item.save()
                messages.success(request, 'Quantity updated!')
            else:
                messages.error(request, 'Invalid quantity.')
        except ValueError:
            messages.error(request, 'Invalid quantity.')
    
    return redirect('cart_view')


def send_cart_email(request):
    """Send cart contents to admin email"""
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
                subject=f'New Quote Request - {customer_name}',
                message=message_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=False,
            )
            
            print("Email sent successfully!")
            
            # Clear cart after sending email
            cart_items.delete()
            
            messages.success(request, 'Your request was sent successfully! We will contact you soon.')
            return redirect('public_catalog')
            
        except Exception as e:
            print(f"Email sending failed: {str(e)}")
            import traceback
            print(f"Full traceback: {traceback.format_exc()}")
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
    
    # Statistics
    stats = {
        'total_games': BoardGame.objects.count(),
        'in_stock': BoardGame.objects.filter(stock_quantity__gt=0, is_sold=False).count(),
        'sold': BoardGame.objects.filter(is_sold=True).count(),
        'total_value': BoardGame.objects.filter(is_sold=False).aggregate(
            total=Sum('final_price')
        )['total'] or 0,
    }
    
    context = {
        'games': games,
        'search_query': search_query,
        'condition_choices': BoardGame.CONDITION_CHOICES,
        'sort_by': sort_by,
        'stats': stats,
    }
    
    return render(request, 'catalog/admin_panel.html', context)
