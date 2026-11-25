"""Email proof for recovering guest quotes and linking them after sign-in."""
import logging

from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from django.urls import reverse

from .models import CustomerQuote
from .whatsapp import quote_message

TOKEN_SALT = 'catalog.guest-quote'
TOKEN_MAX_AGE = 7 * 24 * 60 * 60


def quote_token(quote):
    return signing.dumps({'quote': str(quote.pk), 'email': quote.snapshot['contact']['email']}, salt=TOKEN_SALT)


def read_quote_token(token):
    return signing.loads(token, salt=TOKEN_SALT, max_age=TOKEN_MAX_AGE)


def link_verified_quotes(request, user):
    token = request.session.pop('verified_guest_quote', None)
    if not token:
        return False
    try:
        proof = read_quote_token(token)
    except signing.BadSignature:
        return False
    if proof['email'].casefold() != user.email.casefold():
        return False
    return bool(CustomerQuote.objects.filter(
        user__isnull=True, snapshot__contact__email__iexact=user.email,
    ).update(user=user))


def send_guest_confirmation(quote_id, recovery_url):
    quote = CustomerQuote.objects.get(pk=quote_id)
    try:
        sent = send_mail(
            subject=f'Your game reservation — BG Catalog — {quote.pk}',
            message=('Your games have been reserved for 24 hours. This is not a confirmed sale or payment.\n'
                     'Open WhatsApp from your reservation and press Send to contact the shop.\n\n'
                     f'View your reservation: {recovery_url}\n\n'
                     'This private link expires in 7 days. It also confirms your email so you can '
                     'link guest reservations when you create an account or sign in. Do not share it.\n\n'
                     + quote_message(quote)),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[quote.snapshot['contact']['email']], fail_silently=False,
        )
        if sent != 1:
            raise RuntimeError('Email backend did not accept the message')
    except Exception:
        logging.getLogger(__name__).warning('Guest confirmation email failed for quote %s', quote.pk)


def guest_recovery_url(request, quote):
    return request.build_absolute_uri(reverse('guest_quote_access', args=[quote_token(quote)]))
