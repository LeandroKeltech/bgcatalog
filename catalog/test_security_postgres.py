"""Real row-lock checks; run against PostgreSQL in CI, never emulate in SQLite."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless

from django.contrib.auth import get_user_model
from django.db import connection, connections, close_old_connections
from django.test import Client, TransactionTestCase, override_settings
from django.urls import reverse

from .models import BoardGame, CustomerProfile, CustomerQuote, StockReservation
from .security import consume_limit


@skipUnless(connection.vendor == 'postgresql', 'Requires PostgreSQL row locks')
@override_settings(WHATSAPP_SHOP_NUMBER='+353891234567')
class PostgreSQLSecurityTests(TransactionTestCase):
    def test_concurrent_buyers_cannot_reserve_the_same_last_copy(self):
        game = BoardGame.objects.create(name='Last copy', sale_price=20, stock_quantity=1)
        clients = []
        for index in range(2):
            user = get_user_model().objects.create_user(f'buyer{index}@example.com', email=f'buyer{index}@example.com')
            CustomerProfile.objects.create(user=user, full_name='Buyer', phone='+353891234567')
            client = Client()
            client.force_login(user)
            session = client.session
            session['cart'] = {str(game.pk): 1}
            session.save()
            clients.append(client)
        barrier = Barrier(2)

        def checkout(client):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return client.post(reverse('checkout'))['Location']
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            destinations = list(pool.map(checkout, clients))
        self.assertCountEqual(destinations, [reverse('checkout_success'), reverse('view_cart')])
        self.assertEqual(CustomerQuote.objects.count(), 1)
        self.assertEqual(StockReservation.objects.count(), 1)
        self.assertEqual(game.available_quantity, 0)

    def test_limit_is_atomic_across_database_connections(self):
        barrier = Barrier(2)

        def attempt(index):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return consume_limit('concurrent', 'same-account', 1, 3600)[0]
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(2)))
        self.assertCountEqual(results, [True, False])
