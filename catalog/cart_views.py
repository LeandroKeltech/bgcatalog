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
        messages.error(request, 'Este jogo não está disponível no momento.')
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
            messages.success(request, f'Quantidade de "{game.name}" atualizada no carrinho!')
        else:
            messages.warning(request, f'Quantidade máxima disponível para "{game.name}" já está no carrinho.')
    else:
        messages.success(request, f'"{game.name}" adicionado ao carrinho!')
    
    return redirect('cart_view')


def remove_from_cart(request, pk):
    """Remove item from cart"""
    session_key = get_or_create_session_key(request)
    cart_item = get_object_or_404(CartItem, pk=pk, session_key=session_key)
    
    game_name = cart_item.game.name
    cart_item.delete()
    
    messages.success(request, f'"{game_name}" removido do carrinho.')
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
                messages.success(request, 'Quantidade atualizada!')
            else:
                messages.error(request, 'Quantidade inválida.')
        except ValueError:
            messages.error(request, 'Quantidade inválida.')
    
    return redirect('cart_view')


def send_cart_email(request):
    """Send cart contents to admin email"""
    if request.method == 'POST':
        session_key = get_or_create_session_key(request)
        cart_items = CartItem.objects.filter(session_key=session_key)
        
        if not cart_items.exists():
            messages.error(request, 'Seu carrinho está vazio.')
            return redirect('cart_view')
        
        # Get customer info
        customer_name = request.POST.get('customer_name', 'Cliente')
        customer_email = request.POST.get('customer_email', '')
        customer_phone = request.POST.get('customer_phone', '')
        customer_message = request.POST.get('message', '')
        
        # Build email message
        total = sum(item.subtotal for item in cart_items)
        
        message_body = f"""
Nova solicitação de orçamento do site Board Game Catalog
========================================================

INFORMAÇÕES DO CLIENTE:
Nome: {customer_name}
Email: {customer_email}
Telefone: {customer_phone}

MENSAGEM DO CLIENTE:
{customer_message}

ITENS SOLICITADOS:
{'='*60}

"""
        
        for item in cart_items:
            game = item.game
            message_body += f"""
Jogo: {game.name}
Quantidade: {item.quantity}
Preço Unitário: €{game.final_price:.2f}
Subtotal: €{item.subtotal:.2f}
Condição: {game.get_condition_display()}
Estoque Disponível: {game.stock_quantity}
---
"""
        
        message_body += f"""
{'='*60}
TOTAL: €{total:.2f}
{'='*60}

Esta é uma solicitação de orçamento. Entre em contato com o cliente para confirmar a compra.
"""
        
        try:
            send_mail(
                subject=f'Nova Solicitação de Orçamento - {customer_name}',
                message=message_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMIN_EMAIL],
                fail_silently=False,
            )
            
            # Clear cart after sending email
            cart_items.delete()
            
            messages.success(request, 'Sua solicitação foi enviada com sucesso! Entraremos em contato em breve.')
            return redirect('public_catalog')
            
        except Exception as e:
            messages.error(request, f'Erro ao enviar solicitação. Por favor, tente novamente.')
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
            messages.error(request, 'Usuário ou senha incorretos.')
    
    return render(request, 'catalog/admin_login.html')


def admin_logout(request):
    """Admin logout"""
    auth_logout(request)
    messages.success(request, 'Você saiu da área administrativa.')
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
