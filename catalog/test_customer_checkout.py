from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import BoardGame, CustomerProfile, CustomerQuote, StockReservation


@override_settings(
    WHATSAPP_SHOP_NUMBER='+353 89 123 4567',
    STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}},
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)
class CustomerCheckoutTests(TestCase):
    def test_customer_password_policy_is_simpler_than_admin_policy(self):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        from .customer_forms import CustomerRegistrationForm

        for password in ('584927', 'zibu73', '58492017', 'buyer123'):
            with self.subTest(password=password):
                form = CustomerRegistrationForm(dict(
                    self.signup_data, password1=password, password2=password,
                ))
                self.assertTrue(form.is_valid(), form.errors)
                with self.assertRaises(ValidationError):
                    validate_password(password)
        form = CustomerRegistrationForm(dict(self.signup_data, password1='zib73', password2='zib73'))
        self.assertFalse(form.is_valid())
        self.assertIn('password1', form.errors)
        self.assertContains(self.client.get(reverse('customer_register')), 'at least 6 characters')
        self.assertNotContains(self.client.get(reverse('customer_register')), 'at least 12 characters')

    def setUp(self):
        self.game = BoardGame.objects.create(name='A game & friends', sale_price=20, stock_quantity=3)
        self.signup_data = dict(full_name='Test Buyer', email='BUYER@example.com', phone='+353 89 123 4568',
                                password1='Cloud!cobalt-6942', password2='Cloud!cobalt-6942')
        session = self.client.session
        session['cart'] = {str(self.game.pk): 2}
        session.save()

    def register(self):
        response = self.client.post(reverse('customer_register'), self.signup_data)
        self.assertRedirects(response, reverse('view_cart'))
        return get_user_model().objects.get(username='buyer@example.com')

    def checkout(self):
        response = self.client.post(reverse('checkout'), {
            'customer_name': 'Forged name', 'customer_email': 'other@example.com',
            'customer_phone': 'bad', 'total': '0',
        })
        self.assertRedirects(response, reverse('checkout_success'))
        return CustomerQuote.objects.get()

    def test_registration_preserves_cart_hashes_password_and_cannot_grant_admin(self):
        self.signup_data.update(is_staff='true', is_superuser='true', groups='admin')
        user = self.register()
        self.assertTrue(user.check_password(self.signup_data['password1']))
        self.assertFalse(user.is_staff or user.is_superuser)
        self.assertEqual(list(user.groups.values_list('name', flat=True)), ['user'])
        self.assertEqual(user.customer_profile.phone, '+353891234568')
        self.assertEqual(self.client.session['cart'], {str(self.game.pk): 2})
        self.assertEqual(self.client.get(reverse('admin_panel')).status_code, 403)
        self.assertFalse(StockReservation.objects.exists())

    def test_registration_validates_phone_email_passwords_and_case_insensitive_duplicates(self):
        for change, field in [({'phone': '0891234568'}, 'phone'), ({'email': 'bad'}, 'email'),
                              ({'password2': 'different'}, 'password2'),
                              ({'password1': '12345678', 'password2': '12345678'}, 'password1')]:
            response = self.client.post(reverse('customer_register'), dict(self.signup_data, **change))
            self.assertIn(field, response.context['form'].errors)
            self.assertFalse(CustomerProfile.objects.exists())
        get_user_model().objects.create_user(username='legacy', email='Buyer@Example.COM')
        response = self.client.post(reverse('customer_register'), self.signup_data)
        self.assertIn('email', response.context['form'].errors)

    def test_anonymous_checkout_requires_login_and_does_not_reserve_stock(self):
        response = self.client.post(reverse('checkout'))
        self.assertRedirects(response, reverse('customer_login') + '?next=' + reverse('checkout'))
        self.assertFalse(StockReservation.objects.exists())
        self.assertContains(self.client.get(reverse('view_cart')), 'Create account to check out')

    def test_missing_profile_redirects_to_contact_form(self):
        user = get_user_model().objects.create_user(username='legacy', email='legacy@example.com')
        self.client.force_login(user)
        self.assertRedirects(self.client.post(reverse('checkout')), reverse('customer_account'))
        self.assertFalse(CustomerQuote.objects.exists())
        response = self.client.post(reverse('customer_account'), {
            'full_name': 'Legacy Buyer', 'email': 'tampered@example.com', 'phone': '+353891234568'})
        self.assertRedirects(response, reverse('view_cart'))
        user.refresh_from_db()
        self.assertEqual(user.email, 'legacy@example.com')
        self.assertEqual(user.customer_profile.full_name, 'Legacy Buyer')

    def test_checkout_uses_account_contact_and_prepares_encoded_whatsapp_without_email(self):
        user = self.register()
        quote = self.checkout()
        reservation = quote.reservations.get()
        self.assertEqual(quote.user, user)
        self.assertEqual(reservation.customer_name, 'Test Buyer')
        self.assertEqual(reservation.customer_email, 'buyer@example.com')
        self.assertEqual(reservation.customer_phone, '+353891234568')
        self.assertEqual(quote.snapshot['total'], '40.00')
        self.assertEqual(reservation.quantity, 2)
        self.assertEqual(self.game.available_quantity, 1)
        self.assertEqual(self.client.session['cart'], {})
        self.assertEqual(len(mail.outbox), 0)
        response = self.client.get(reverse('customer_quote', args=[quote.pk]))
        parsed = urlparse(response.context['whatsapp_url'])
        self.assertEqual((parsed.scheme, parsed.netloc, parsed.path), ('https', 'wa.me', '/353891234567'))
        message = parse_qs(parsed.query)['text'][0]
        for text in (str(quote.pk), 'Test Buyer', user.email, '+353891234568',
                     '2 × A game & friends', 'Total: €40.00', 'Reservation expires:'):
            self.assertIn(text, message)
        self.assertContains(response, 'no message has been sent yet')
        self.assertIn('no-store', response.headers['Cache-Control'])
        self.assertNotContains(response, 'Forged name')

    def test_checkout_success_refresh_and_repeated_submit_do_not_duplicate_reservations(self):
        self.register()
        quote = self.checkout()
        for _ in range(2):
            self.assertContains(self.client.get(reverse('checkout_success')), str(quote.pk))
        self.assertRedirects(self.client.post(reverse('checkout')), reverse('view_cart'))
        self.assertEqual(CustomerQuote.objects.count(), 1)
        self.assertEqual(StockReservation.objects.count(), 1)

    def test_another_account_cannot_read_quote_or_contact_details(self):
        self.register()
        quote = self.checkout()
        self.client.logout()
        url = reverse('customer_quote', args=[quote.pk])
        self.assertRedirects(self.client.get(url), reverse('customer_login') + '?next=' + url)
        other = get_user_model().objects.create_user(username='other@example.com', email='other@example.com')
        self.client.force_login(other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertNotContains(self.client.get(reverse('customer_account')), str(quote.pk))

    def test_snapshot_survives_catalog_and_contact_edits(self):
        user = self.register()
        quote = self.checkout()
        BoardGame.objects.filter(pk=self.game.pk).update(name='Renamed', sale_price=99)
        CustomerProfile.objects.filter(user=user).update(full_name='New name', phone='+353891234569')
        response = self.client.get(reverse('customer_quote', args=[quote.pk]))
        self.assertContains(response, 'A game &amp; friends')
        self.assertContains(response, '€40.00')
        self.assertIn('Name: Test Buyer', response.context['whatsapp_message'])
        self.assertNotIn('New name', response.context['whatsapp_message'])

    def test_admin_can_match_whatsapp_reference_and_phone_to_reservations(self):
        self.register()
        quote = self.checkout()
        from django.contrib.auth.models import Group
        admin = get_user_model().objects.create_user(username='shop-admin')
        admin.groups.add(Group.objects.get(name='admin'))
        self.client.force_login(admin)
        response = self.client.get(reverse('reservation_management'))
        self.assertContains(response, str(quote.pk))
        self.assertContains(response, '+353891234568')

    def test_expired_cancelled_and_processed_quotes_remain_readable_without_active_link(self):
        self.register()
        quote = self.checkout()
        for status in ('active', 'cancelled', 'confirmed'):
            StockReservation.objects.update(status=status, expires_at=timezone.now() - timedelta(seconds=1))
            response = self.client.get(reverse('customer_quote', args=[quote.pk]))
            self.assertIsNone(response.context['whatsapp_url'])
            self.assertContains(response, 'This reservation is no longer active')
            self.assertNotContains(response, 'https://wa.me/')

    @override_settings(WHATSAPP_SHOP_NUMBER='')
    def test_missing_shop_number_does_not_create_hold_or_lose_cart(self):
        self.register()
        response = self.client.post(reverse('checkout'), follow=True)
        self.assertContains(response, 'WhatsApp checkout is temporarily unavailable')
        self.assertFalse(StockReservation.objects.exists())
        self.assertFalse(CustomerQuote.objects.exists())
        self.assertEqual(self.client.session['cart'], {str(self.game.pk): 2})

    def test_stock_failure_rolls_back_quote_and_keeps_cart(self):
        self.register()
        BoardGame.objects.filter(pk=self.game.pk).update(stock_quantity=1)
        self.assertRedirects(self.client.post(reverse('checkout')), reverse('view_cart'))
        self.assertFalse(CustomerQuote.objects.exists())
        self.assertFalse(StockReservation.objects.exists())
        self.assertEqual(self.client.session['cart'], {str(self.game.pk): 2})

    def test_email_login_keeps_cart_and_logout_requires_post(self):
        self.register()
        self.assertEqual(self.client.get(reverse('customer_logout')).status_code, 405)
        self.client.post(reverse('customer_logout'))
        self.client.post(reverse('add_to_cart', args=[self.game.pk]), {'quantity': 1})
        response = self.client.post(reverse('customer_login'), {'username': 'BUYER@EXAMPLE.COM', 'password': 'wrong'})
        self.assertTrue(response.context['form'].errors)
        response = self.client.post(reverse('customer_login'), {
            'username': 'BUYER@EXAMPLE.COM', 'password': self.signup_data['password1']})
        self.assertRedirects(response, reverse('view_cart'))
        self.assertEqual(self.client.session['cart'], {str(self.game.pk): 1})

    def test_public_forms_enforce_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        for route in ('customer_register', 'customer_login', 'customer_logout'):
            self.assertEqual(csrf_client.post(reverse(route), self.signup_data).status_code, 403)
