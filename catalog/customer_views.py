from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from django.core.exceptions import ImproperlyConfigured
from django.core import signing
from django.contrib.auth.views import redirect_to_login
from django.http import Http404
from django.urls import reverse

from .customer_forms import CustomerRegistrationForm, CustomerLoginForm, CustomerContactForm
from .models import CustomerProfile, CustomerQuote
from .whatsapp import quote_message, whatsapp_url
from .guest_quotes import read_quote_token, link_verified_quotes


@never_cache
def customer_register(request):
    if request.user.is_authenticated:
        return redirect('view_cart')
    initial = {}
    token = request.session.get('verified_guest_quote')
    if token:
        try:
            initial['email'] = read_quote_token(token)['email']
        except signing.BadSignature:
            pass
    form = CustomerRegistrationForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        try:
            user = form.save()
        except IntegrityError:
            form.add_error('email', 'This account could not be created. Try signing in with your email.')
        else:
            login(request, user)
            if link_verified_quotes(request, user):
                messages.success(request, 'Your verified guest reservations are now saved in your account.')
                return redirect('customer_account')
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
        if link_verified_quotes(request, form.get_user()):
            messages.success(request, 'Your verified guest reservations are now saved in your account.')
            return redirect('customer_account')
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
def customer_quote(request, quote_id):
    quotes = CustomerQuote.objects.prefetch_related('reservations')
    if request.user.is_authenticated and quotes.filter(pk=quote_id, user=request.user).exists():
        quote = quotes.get(pk=quote_id, user=request.user)
    elif str(quote_id) in request.session.get('guest_quote_ids', []):
        quote = get_object_or_404(quotes, pk=quote_id, user__isnull=True)
    elif not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path(), reverse('customer_login'))
    else:
        raise Http404
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


@never_cache
def guest_quote_access(request, token):
    try:
        proof = read_quote_token(token)
    except signing.BadSignature:
        messages.error(request, 'This reservation link is invalid or expired.')
        return redirect('view_cart')
    quote = get_object_or_404(CustomerQuote, pk=proof['quote'], snapshot__contact__email=proof['email'])
    request.session['verified_guest_quote'] = token
    guest_ids = request.session.get('guest_quote_ids', [])
    request.session['guest_quote_ids'] = (guest_ids + [str(quote.pk)])[-50:]
    response = redirect('customer_quote', quote_id=quote.pk)
    response['Referrer-Policy'] = 'no-referrer'
    return response


@require_POST
@login_required(login_url='customer_login')
def claim_guest_quotes(request):
    if link_verified_quotes(request, request.user):
        messages.success(request, 'Your verified guest reservations are now saved in your account.')
    else:
        messages.error(request, 'Open the reservation email link for your account email before linking reservations.')
    return redirect('customer_account')
