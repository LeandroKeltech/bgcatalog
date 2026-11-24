from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.core.exceptions import ImproperlyConfigured

from .customer_forms import CustomerRegistrationForm, CustomerLoginForm, CustomerContactForm
from .models import CustomerProfile, CustomerQuote
from .whatsapp import quote_message, whatsapp_url


@never_cache
def customer_register(request):
    if request.user.is_authenticated:
        return redirect('view_cart')
    form = CustomerRegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            user = form.save()
        except IntegrityError:
            form.add_error('email', 'This account could not be created. Try signing in with your email.')
        else:
            login(request, user)
            messages.success(request, 'Account created. Your cart is ready to review.')
            return redirect('view_cart')
    return render(request, 'catalog/customer_register.html', {'form': form})


@never_cache
def customer_login(request):
    if request.user.is_authenticated:
        return redirect('view_cart')
    form = CustomerLoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        return redirect('view_cart')
    return render(request, 'catalog/customer_login.html', {'form': form})


@require_POST
def customer_logout(request):
    logout(request)
    return redirect('catalog')


@never_cache
@login_required(login_url='customer_login')
def customer_account(request):
    profile = CustomerProfile.objects.filter(user=request.user).first()
    initial = {'email': request.user.email, 'full_name': profile.full_name if profile else '',
               'phone': profile.phone if profile else ''}
    form = CustomerContactForm(request.POST or None, user=request.user, initial=initial)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Contact details saved.')
        return redirect('view_cart')
    return render(request, 'catalog/customer_account.html', {
        'form': form, 'quotes': request.user.customer_quotes.all()[:20],
    })


@never_cache
@login_required(login_url='customer_login')
def customer_quote(request, quote_id):
    quote = get_object_or_404(CustomerQuote.objects.prefetch_related('reservations'), pk=quote_id, user=request.user)
    message = quote_message(quote)
    link = None
    if quote.is_active:
        try:
            link = whatsapp_url(message)
        except ImproperlyConfigured:
            messages.error(request, 'WhatsApp checkout is temporarily unavailable. You can copy your saved message below.')
    return render(request, 'catalog/checkout_success.html', {
        'quote': quote, 'whatsapp_url': link,
        'whatsapp_message': message,
    })
