from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import BoardGame


@override_settings(STORAGES={
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class CustomerEmailLoginTests(TestCase):
    password = 'Test-only-cobalt-6842'

    def sign_in(self, email, password=None):
        return self.client.post(reverse('customer_login'), {
            'username': email, 'password': password or self.password,
        })

    def test_existing_account_signs_in_by_email_when_username_is_different(self):
        user = get_user_model().objects.create_user(
            username='legacy-buyer', email='buyer@example.com', password=self.password,
        )
        original_hash = user.password
        game = BoardGame.objects.create(name='Saved cart game', sale_price=10, stock_quantity=2)
        session = self.client.session
        session['cart'] = {str(game.pk): 1}
        session.save()
        self.assertRedirects(self.sign_in('buyer@example.com'), reverse('view_cart'))
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)
        self.assertEqual(self.client.session['cart'], {str(game.pk): 1})
        user.refresh_from_db()
        self.assertEqual(user.username, 'legacy-buyer')
        self.assertEqual(user.password, original_hash)

    def test_email_lookup_ignores_case_and_surrounding_spaces(self):
        user = get_user_model().objects.create_user(
            username='LegacyBuyer', email='Buyer@Example.COM', password=self.password,
        )
        self.assertRedirects(self.sign_in(' BUYER@example.com '), reverse('view_cart'))
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_duplicate_email_is_rejected_instead_of_selecting_an_account(self):
        get_user_model().objects.create_user('first-buyer', email='buyer@example.com', password=self.password)
        get_user_model().objects.create_user('second-buyer', email='BUYER@example.com', password='Other-only-7348')
        response = self.sign_in('buyer@example.com')
        self.assertContains(response, 'The email or password is incorrect. Please try again.')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_email_is_not_confused_with_another_accounts_username(self):
        other = get_user_model().objects.create_user(
            username='buyer@example.com', email='other@example.com', password='Other-only-7348',
        )
        intended = get_user_model().objects.create_user(
            username='legacy-buyer', email='buyer@example.com', password=self.password,
        )
        response = self.sign_in('buyer@example.com', 'Other-only-7348')
        self.assertContains(response, 'The email or password is incorrect. Please try again.')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertRedirects(self.sign_in('buyer@example.com'), reverse('view_cart'))
        self.assertEqual(int(self.client.session['_auth_user_id']), intended.pk)
        self.assertNotEqual(int(self.client.session['_auth_user_id']), other.pk)

    def test_unknown_inactive_and_wrong_password_use_the_same_error(self):
        get_user_model().objects.create_user('legacy-buyer', email='buyer@example.com', password=self.password)
        get_user_model().objects.create_user('inactive-buyer', email='inactive@example.com',
                                             password=self.password, is_active=False)
        for email, password in (
            ('unknown@example.com', self.password),
            ('buyer@example.com', 'Wrong-only-4938'),
            ('inactive@example.com', self.password),
        ):
            with self.subTest(email=email):
                response = self.sign_in(email, password)
                self.assertContains(response, 'The email or password is incorrect. Please try again.')
                self.assertNotIn('_auth_user_id', self.client.session)
                self.assertNotContains(response, password)
