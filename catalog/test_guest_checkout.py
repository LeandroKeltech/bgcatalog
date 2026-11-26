import time
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .guest_quotes import quote_token, TOKEN_MAX_AGE
from .models import BoardGame, CustomerProfile, CustomerQuote, StockReservation


@override_settings(
    WHATSAPP_SHOP_NUMBER='+353891234567',
    STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}},
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    RESERVATION_NOTIFICATION_EMAIL='',
)
class GuestCheckoutTests(TestCase):
    def setUp(self):
        self.game = BoardGame.objects.create(name='Guest game', sale_price=20, stock_quantity=20)
        self.fill_cart()

    def fill_cart(self, client=None):
        client = client or self.client
        session = client.session
        session['cart'] = {str(self.game.pk): 2}
        session.save()

    def checkout(self, email='GUEST@example.com'):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('checkout'), {'email': email, 'total': '0'})
        self.assertRedirects(response, reverse('checkout_success'))
        return CustomerQuote.objects.latest('created_at')

    def test_email_only_reserves_without_user_and_emails_private_recovery_link(self):
        quote = self.checkout()
        self.assertIsNone(quote.user)
        self.assertFalse(get_user_model().objects.exists())
        self.assertFalse(CustomerProfile.objects.exists())
        reservation = quote.reservations.get()
        self.assertEqual(reservation.customer_email, 'guest@example.com')
        self.assertEqual(reservation.customer_phone, '')
        self.assertEqual(reservation.customer_name, '')
        self.assertEqual(quote.snapshot['total'], '40.00')
        self.assertEqual(self.game.available_quantity, 18)
        self.assertEqual(self.client.session['cart'], {})
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ['guest@example.com'])
        self.assertIn('http://testserver/account/guest-reservations/', mail.outbox[0].body)
        html, mimetype = mail.outbox[0].alternatives[0]
        self.assertEqual(mimetype, 'text/html')
        self.assertIn('Prices are for collection.', html)
        self.assertIn('This private link expires in 7 days.', html)
        self.assertIn('Guest game', html)
        response = self.client.get(reverse('checkout_success'))
        self.assertContains(response, 'No account has been created')
        self.assertContains(response, 'Open WhatsApp &amp; send order')
        self.assertIn('Email: guest@example.com', response.context['whatsapp_message'])
        self.assertNotIn('Phone:', response.context['whatsapp_message'])
        self.assertIn('no-store', response.headers['Cache-Control'])
        self.client.get(reverse('checkout_success'))
        self.assertRedirects(self.client.post(reverse('checkout'), {'email': 'guest@example.com'}), reverse('view_cart'))
        self.assertEqual(CustomerQuote.objects.count(), 1)

    def test_invalid_email_keeps_cart_without_reservations(self):
        for email in ('', 'invalid'):
            response = self.client.post(reverse('checkout'), {'email': email})
            self.assertEqual(response.status_code, 400)
            self.assertIn('email', response.context['guest_form'].errors)
        self.assertFalse(StockReservation.objects.exists())
        self.assertEqual(self.client.session['cart'], {str(self.game.pk): 2})

    def test_email_matching_existing_account_does_not_grant_history_or_ownership(self):
        user = get_user_model().objects.create_user('guest@example.com', email='guest@example.com', password='Cloud!cobalt-6942')
        quote = self.checkout()
        self.assertIsNone(quote.user_id)
        other = Client()
        url = reverse('customer_quote', args=[quote.pk])
        self.assertRedirects(other.get(url), reverse('customer_login') + '?next=' + url)
        other.force_login(user)
        self.assertEqual(other.get(url).status_code, 404)
        self.assertNotContains(other.get(reverse('customer_account')), str(quote.pk))
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_email_link_recovers_quote_and_links_history_after_registration(self):
        quote = self.checkout()
        browser = Client()
        self.assertRedirects(browser.get(reverse('guest_quote_access', args=[quote_token(quote)])),
                             reverse('customer_quote', args=[quote.pk]))
        self.assertContains(browser.get(reverse('customer_register')), 'value="guest@example.com"')
        response = browser.post(reverse('customer_register'), {
            'full_name': 'Guest Buyer', 'email': 'guest@example.com', 'phone': '+353891234568',
            'password1': 'Cloud!cobalt-6942', 'password2': 'Cloud!cobalt-6942',
        })
        self.assertRedirects(response, reverse('customer_account'))
        quote.refresh_from_db()
        self.assertEqual(quote.user.email, 'guest@example.com')
        self.assertContains(browser.get(reverse('customer_account')), str(quote.pk)[:10])

    def test_signup_without_email_proof_does_not_claim_guest_history(self):
        quote = self.checkout()
        response = self.client.post(reverse('customer_register'), {
            'full_name': 'Unverified Buyer', 'email': 'guest@example.com', 'phone': '+353891234568',
            'password1': 'Cloud!cobalt-6942', 'password2': 'Cloud!cobalt-6942',
        })
        self.assertRedirects(response, reverse('view_cart'))
        quote.refresh_from_db()
        self.assertIsNone(quote.user_id)
        self.assertNotContains(self.client.get(reverse('customer_account')), str(quote.pk)[:10])

    def test_existing_account_can_claim_only_after_email_proof(self):
        user = get_user_model().objects.create_user('guest@example.com', email='guest@example.com', password='Cloud!cobalt-6942')
        quote = self.checkout()
        browser = Client()
        browser.get(reverse('guest_quote_access', args=[quote_token(quote)]))
        response = browser.post(reverse('customer_login'), {'username': user.email, 'password': 'Cloud!cobalt-6942'})
        self.assertRedirects(response, reverse('customer_account'))
        quote.refresh_from_db()
        self.assertEqual(quote.user_id, user.pk)
        self.assertEqual(self.client.get(reverse('customer_quote', args=[quote.pk])).status_code, 404)

    def test_tampered_expired_or_different_email_cannot_claim(self):
        quote = self.checkout()
        token = quote_token(quote)
        browser = Client()
        self.assertRedirects(browser.get(reverse('guest_quote_access', args=[token + 'x'])), reverse('view_cart'))
        with patch('django.core.signing.time.time', return_value=time.time() + TOKEN_MAX_AGE + 2):
            self.assertRedirects(browser.get(reverse('guest_quote_access', args=[token])), reverse('view_cart'))
        browser.get(reverse('guest_quote_access', args=[token]))
        user = get_user_model().objects.create_user('other', email='other@example.com')
        browser.force_login(user)
        self.assertEqual(browser.get(reverse('claim_guest_quotes')).status_code, 405)
        browser.post(reverse('claim_guest_quotes'))
        quote.refresh_from_db()
        self.assertIsNone(quote.user_id)

    def test_failed_email_delivery_does_not_rollback_reservation(self):
        with patch('catalog.guest_quotes.send_mail', side_effect=RuntimeError('SMTP unavailable')):
            quote = self.checkout()
        self.assertTrue(quote.is_active)
        self.assertContains(self.client.get(reverse('checkout_success')), str(quote.pk))

    def test_signed_in_account_can_link_verified_guest_quotes_with_post(self):
        quote = self.checkout()
        user = get_user_model().objects.create_user('guest@example.com', email='guest@example.com')
        self.client.force_login(user)
        self.client.post(reverse('claim_guest_quotes'))
        quote.refresh_from_db()
        self.assertIsNone(quote.user_id)
        self.client.get(reverse('guest_quote_access', args=[quote_token(quote)]))
        response = self.client.post(reverse('claim_guest_quotes'))
        self.assertRedirects(response, reverse('customer_account'))
        quote.refresh_from_db()
        self.assertEqual(quote.user_id, user.pk)

    def test_unavailable_stock_keeps_guest_cart_and_sends_no_confirmation(self):
        BoardGame.objects.filter(pk=self.game.pk).update(stock_quantity=1)
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(reverse('checkout'), {'email': 'guest@example.com'})
        self.assertRedirects(response, reverse('view_cart'))
        self.assertFalse(CustomerQuote.objects.exists())
        self.assertFalse(StockReservation.objects.exists())
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(self.client.session['cart'], {str(self.game.pk): 2})

    def test_guest_quote_cap_and_rate_limit_preserve_stock(self):
        for _ in range(3):
            self.checkout()
            self.fill_cart()
        self.assertRedirects(self.client.post(reverse('checkout'), {'email': 'guest@example.com'}), reverse('view_cart'))
        self.assertEqual(CustomerQuote.objects.count(), 3)
        self.assertEqual(self.game.available_quantity, 14)
        self.client.post(reverse('checkout'), {'email': 'guest@example.com'})
        self.assertEqual(self.client.post(reverse('checkout'), {'email': 'guest@example.com'}).status_code, 429)

    def test_guest_checkout_requires_csrf(self):
        browser = Client(enforce_csrf_checks=True)
        self.fill_cart(browser)
        self.assertEqual(browser.post(reverse('checkout'), {'email': 'guest@example.com'}).status_code, 403)
        self.assertFalse(StockReservation.objects.exists())
