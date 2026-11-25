"""Shared database limits across workers and serverless instances."""
import ipaddress
import math
import time
from datetime import datetime, timezone

from django.conf import settings
from django.db import DatabaseError
from django.db.models import F
from django.http import HttpResponse
from django.utils.cache import add_never_cache_headers
from django.utils.crypto import salted_hmac
from django.utils.deprecation import MiddlewareMixin

from .models import SecurityRateLimit


def client_ip(request):
    header = settings.RATE_LIMIT_IP_HEADER
    value = request.META.get(header, '') if header else ''
    value = value or request.META.get('REMOTE_ADDR', '')
    try:
        address = ipaddress.ip_address(value.strip())
        return str(ipaddress.ip_network(f'{address}/64', strict=False)) if address.version == 6 else str(address)
    except ValueError:
        return 'unknown'


def consume_limit(scope, identity, limit, seconds):
    now = time.time()
    bucket = int(now // seconds)
    digest = salted_hmac('catalog.rate-limit', f'{scope}:{identity}:{bucket}', algorithm='sha256').hexdigest()
    end = (bucket + 1) * seconds
    SecurityRateLimit.objects.get_or_create(
        key=digest, defaults={'expires_at': datetime.fromtimestamp(end, timezone.utc)},
    )
    # One conditional UPDATE prevents concurrent workers exceeding the cap.
    allowed = SecurityRateLimit.objects.filter(key=digest, attempts__lt=limit).update(attempts=F('attempts') + 1)
    return bool(allowed), max(1, math.ceil(end - now))


class SecurityMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.method != 'POST':
            return None
        name = request.resolver_match.view_name
        ip = client_ip(request)
        rules = []
        if name in ('admin:login', 'customer_login'):
            username = request.POST.get('username', '').strip().casefold()[:254]
            rules = [('login-ip', ip, 30, 900), ('login-account', username, 10, 900)]
        elif name == 'customer_register':
            rules = [('register-ip', ip, 5, 3600)]
        elif name == 'checkout':
            rules = [('checkout-ip', ip, 20, 1800)]
            if request.user.is_authenticated:
                rules.append(('checkout-account', str(request.user.pk), 5, 1800))
            else:
                email = request.POST.get('email', '').strip().casefold()[:150]
                rules.append(('checkout-email', email, 5, 1800))
        try:
            for rule in rules:
                allowed, retry = consume_limit(*rule)
                if not allowed:
                    response = HttpResponse('Too many attempts. Please try again later.', status=429)
                    response['Retry-After'] = str(retry)
                    return response
        except DatabaseError:
            return HttpResponse('Temporarily unavailable. Please try again later.', status=503)
        return None

    def process_response(self, request, response):
        if request.path.startswith(('/account/', '/admin/', '/admin-panel/', '/cart/', '/checkout/')):
            add_never_cache_headers(response)
            response['Cache-Control'] += ', private'
        response['Permissions-Policy'] = 'camera=(self), microphone=(), geolocation=()'
        return response
