from django.test import TestCase, override_settings
from django.urls import reverse

from .models import BoardGame, StockReservation


@override_settings(
    STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}},
)
class CartDrawerTests(TestCase):
    def setUp(self):
        self.game = BoardGame.objects.create(name='One copy game', sale_price=20, stock_quantity=1)
        self.url = reverse('add_to_cart', args=[self.game.pk])

    def add(self, quantity=1):
        return self.client.post(self.url, {'quantity': quantity}, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

    def test_repeated_add_at_stock_limit_returns_existing_cart_without_error(self):
        self.assertEqual(self.add().status_code, 200)
        for _ in range(2):
            response = self.add()
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()['ok'])
            self.assertTrue(response.json()['already_in_cart'])
            self.assertEqual(response.json()['cart_count'], 1)
            self.assertIn('already in your cart', response.json()['message'])
            self.assertEqual(self.client.session['cart'], {str(self.game.pk): 1})
        self.assertContains(self.client.get(reverse('view_cart'), {'drawer': '1'}), self.game.name)
        self.game.refresh_from_db()
        self.assertEqual(self.game.stock_quantity, 1)
        self.assertFalse(StockReservation.objects.exists())

    def test_repeated_add_still_increments_when_more_stock_is_available(self):
        self.game.stock_quantity = 3
        self.game.save()
        self.add()
        response = self.add()
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json().get('already_in_cart', False))
        self.assertEqual(self.client.session['cart'], {str(self.game.pk): 2})

    def test_first_add_above_stock_is_rejected(self):
        self.assertEqual(self.add(2).status_code, 400)
        self.assertFalse(self.client.session.get('cart'))

    def test_invalid_quantity_is_rejected_even_when_game_is_in_cart(self):
        self.add()
        for quantity in (0, -1, 'invalid'):
            self.assertEqual(self.add(quantity).status_code, 400)
            self.assertEqual(self.client.session['cart'], {str(self.game.pk): 1})

    def test_sold_out_game_is_rejected_even_when_game_is_in_cart(self):
        self.add()
        self.game.stock_quantity = 0
        self.game.save()
        self.assertEqual(self.add().status_code, 400)
        self.assertEqual(self.client.session['cart'], {str(self.game.pk): 1})

    def test_repeated_add_without_javascript_redirects_to_cart(self):
        self.client.post(self.url, {'quantity': 1})
        response = self.client.post(self.url, {'quantity': 1})
        self.assertRedirects(response, reverse('view_cart'))
        self.assertEqual(self.client.session['cart'], {str(self.game.pk): 1})
