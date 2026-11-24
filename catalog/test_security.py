import sqlite3
from contextlib import closing
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import OperationalError
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse

from .models import BoardGame, CustomerProfile, CustomerQuote, SecurityRateLimit, StockReservation
from .security import client_ip, consume_limit


@override_settings(
    WHATSAPP_SHOP_NUMBER='+353891234567',
    STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}},
)
class SecurityTests(TestCase):
    def test_external_integrations_reject_invalid_certificates(self):
        import requests
        from . import bgg_price_service
        for function, argument in (
            (bgg_price_service._search_bgg_web_scraping, 'Game'),
            (bgg_price_service.fetch_bgg_thumbnail, '123'),
            (bgg_price_service.scrape_bgg_game_page, '123'),
        ):
            with patch('catalog.bgg_price_service.requests.get', side_effect=requests.exceptions.SSLError('invalid certificate')) as get:
                self.assertFalse(function(argument))
                self.assertIsNot(get.call_args.kwargs.get('verify', True), False)

    def test_login_limit_cannot_be_bypassed_by_switching_entry_point_or_ip(self):
        with patch('catalog.security.time.time', return_value=1801):
            for index in range(10):
                route = 'admin:login' if index % 2 else 'customer_login'
                response = self.client.post(reverse(route), {'username': 'Unknown@example.com', 'password': 'wrong'},
                                            REMOTE_ADDR=f'192.0.2.{index + 1}')
                self.assertEqual(response.status_code, 200)
            response = Client().post(reverse('customer_login'), {'username': 'UNKNOWN@example.com', 'password': 'wrong'},
                                     REMOTE_ADDR='198.51.100.10')
            self.assertEqual(response.status_code, 429)
            self.assertEqual(response['Retry-After'], '899')
            keys = list(SecurityRateLimit.objects.values_list('key', flat=True))
            self.assertTrue(all(len(key) == 64 and 'example' not in key for key in keys))

    def test_login_ip_limit_blocks_rotating_usernames(self):
        with patch('catalog.security.time.time', return_value=1801):
            for index in range(30):
                self.client.post(reverse('customer_login'), {'username': f'{index}@example.com', 'password': 'wrong'})
            response = self.client.post(reverse('admin:login'), {'username': 'fresh', 'password': 'wrong'})
            self.assertEqual(response.status_code, 429)

    def test_limit_expires_and_does_not_reset_for_a_different_process(self):
        with patch('catalog.security.time.time', return_value=1801):
            self.assertTrue(consume_limit('scope', 'account', 1, 900)[0])
            self.assertFalse(consume_limit('scope', 'account', 1, 900)[0])
        with patch('catalog.security.time.time', return_value=2701):
            self.assertTrue(consume_limit('scope', 'account', 1, 900)[0])

    @override_settings(RATE_LIMIT_IP_HEADER='')
    def test_untrusted_forwarded_header_cannot_change_rate_limit_identity(self):
        request = RequestFactory().get('/', REMOTE_ADDR='192.0.2.1', HTTP_X_FORWARDED_FOR='198.51.100.1')
        self.assertEqual(client_ip(request), '192.0.2.1')
        request.META['REMOTE_ADDR'] = '2001:db8::1234'
        self.assertEqual(client_ip(request), '2001:db8::/64')

    @override_settings(RATE_LIMIT_IP_HEADER='HTTP_X_VERCEL_FORWARDED_FOR')
    def test_hosting_provider_header_is_used_when_configured(self):
        request = RequestFactory().get('/', REMOTE_ADDR='127.0.0.1', HTTP_X_VERCEL_FORWARDED_FOR='192.0.2.2')
        self.assertEqual(client_ip(request), '192.0.2.2')

    def test_counter_failure_does_not_disable_protection(self):
        with patch('catalog.security.consume_limit', side_effect=OperationalError('private db details')):
            response = self.client.post(reverse('customer_login'), {})
        self.assertEqual(response.status_code, 503)
        self.assertNotContains(response, 'private db details', status_code=503)

    def test_registration_and_checkout_have_separate_limits(self):
        for _ in range(5):
            self.assertEqual(self.client.post(reverse('customer_register'), {}).status_code, 200)
        self.assertEqual(self.client.post(reverse('customer_register'), {}).status_code, 429)
        user = get_user_model().objects.create_user('buyer@example.com', email='buyer@example.com')
        self.client.force_login(user)
        for _ in range(5):
            self.assertEqual(self.client.post(reverse('checkout'), {}).status_code, 302)
        self.assertEqual(self.client.post(reverse('checkout'), {}).status_code, 429)

    def test_active_quote_cap_preserves_cart_and_stock(self):
        user = get_user_model().objects.create_user('buyer@example.com', email='buyer@example.com')
        CustomerProfile.objects.create(user=user, full_name='Buyer', phone='+353891234567')
        game = BoardGame.objects.create(name='Game', sale_price=20, stock_quantity=20)
        self.client.force_login(user)
        for index in range(4):
            session = self.client.session
            session['cart'] = {str(game.pk): 1}
            session.save()
            response = self.client.post(reverse('checkout'))
            self.assertEqual(response.status_code, 302)
            self.assertEqual(CustomerQuote.objects.count(), min(index + 1, 3))
        self.assertEqual(StockReservation.objects.count(), 3)
        self.assertEqual(self.client.session['cart'], {str(game.pk): 1})
        self.assertEqual(game.available_quantity, 17)

    def test_refresh_requires_post_and_csrf_even_for_admin(self):
        user = get_user_model().objects.create_superuser('owner', password='Private-test-582!')
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse('refresh_game_data', args=[1])).status_code, 405)
        client = Client(enforce_csrf_checks=True)
        client.force_login(user)
        self.assertEqual(client.post(reverse('refresh_game_data', args=[1])).status_code, 403)

    def test_sensitive_pages_are_not_cached(self):
        for name in ('customer_login', 'customer_register', 'view_cart', 'admin:login'):
            response = self.client.get(reverse(name))
            self.assertIn('no-store', response['Cache-Control'])
            self.assertIn('private', response['Cache-Control'])

    @override_settings(
        SECURE_SSL_REDIRECT=True, SECURE_HSTS_SECONDS=3600,
        SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True,
    )
    def test_https_redirect_headers_and_secure_csrf_cookie(self):
        url = reverse('customer_login')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response['Location'].startswith('https://'))
        response = self.client.get(url, secure=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('max-age=3600', response['Strict-Transport-Security'])
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(response['Referrer-Policy'], 'same-origin')
        self.assertTrue(response.cookies['csrftoken']['secure'])

    def test_sqlite_backup_can_be_restored_and_cannot_overwrite_or_be_public(self):
        with TemporaryDirectory(dir=settings.BASE_DIR) as folder:
            source = Path(folder) / 'source.sqlite3'
            target = Path(folder) / 'backup.sqlite3'
            with closing(sqlite3.connect(source)) as db:
                db.execute('CREATE TABLE example (value TEXT)')
                db.execute("INSERT INTO example VALUES ('recoverable data')")
                db.commit()
            databases = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': str(source)}}
            with override_settings(DATABASES=databases):
                call_command('backup_database', output=str(target), stdout=StringIO())
                with closing(sqlite3.connect(target)) as restored:
                    self.assertEqual(restored.execute('SELECT value FROM example').fetchone()[0], 'recoverable data')
                with self.assertRaises(CommandError):
                    call_command('backup_database', output=str(target), stdout=StringIO())
                with override_settings(MEDIA_ROOT=Path(folder)):
                    with self.assertRaises(CommandError):
                        call_command('backup_database', output=str(Path(folder) / 'public.sqlite3'), stdout=StringIO())
