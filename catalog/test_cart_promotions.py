from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .cart_pricing import price_cart
from .finance import confirm_reserved_sale, ledger_summary, record_cash, update_reservation
from .forms import PromotionForm
from .models import BoardGame, Promotion, Sale, StockReservation, CustomerProfile
from .whatsapp import quote_message
from .pricing import with_selling_price


@override_settings(
    STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}},
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    WHATSAPP_SHOP_NUMBER='+353891234567',
)
class CartPromotionTests(TestCase):
    def setUp(self):
        self.games = [BoardGame.objects.create(name=f'Game {price}', sale_price=price, stock_quantity=20)
                      for price in (50, 40, 30, 20, 10)]
        self.user = get_user_model().objects.create_user(username='staff', is_staff=True)
        self.user.groups.add(Group.objects.get_or_create(name='admin')[0])
        customer = get_user_model().objects.create_user(username='buyer@example.com', email='buyer@example.com')
        CustomerProfile.objects.create(user=customer, full_name='Buyer', phone='+353891234568')
        self.client.force_login(customer)

    def offer(self, **kwargs):
        values = dict(name='Buy five, pay for four', kind='cheapest_free', value=0,
                      minimum_quantity=5, apply_to_all=True,
                      starts_at=timezone.now() - timedelta(hours=1))
        values.update(kwargs)
        return Promotion.objects.create(**values)

    def quote(self, quantities=None):
        cart = quantities or {str(game.pk): 1 for game in self.games}
        return price_cart(cart, BoardGame.objects.in_bulk(cart.keys()))

    def checkout(self, quantities=None):
        cart = quantities or {str(game.pk): 1 for game in self.games}
        session = self.client.session
        session['cart'] = cart
        session.save()
        return self.client.post(reverse('checkout'), {'customer_name': 'Buyer', 'customer_email': 'buyer@example.com'})

    def test_cheapest_of_five_is_free_and_does_not_change_catalog_prices(self):
        promotion = self.offer()
        quote = self.quote()
        self.assertEqual(quote['subtotal'], Decimal('150'))
        self.assertEqual(quote['total'], Decimal('140'))
        self.assertEqual(quote['discount'], Decimal('10'))
        self.assertEqual(quote['applied_promotion'], promotion)
        self.assertEqual(quote['cart_items'][-1]['price_groups'], [(Decimal('0'), 1)])
        game = with_selling_price(BoardGame.objects.all()).get(pk=self.games[-1].pk)
        self.assertEqual(game.selling_price, Decimal('10'))
        self.assertEqual(game.final_price, Decimal('10'))

    def test_below_threshold_shows_progress_without_discount(self):
        self.offer()
        quote = self.quote({str(self.games[0].pk): 2})
        self.assertEqual(quote['total'], Decimal('100'))
        self.assertEqual(quote['cart_offers'][0]['missing'], 3)
        self.assertIsNone(quote['applied_promotion'])

    def test_buy_two_percentage_applies_to_all_eligible_copies(self):
        self.offer(kind='cart_percentage', value=10, minimum_quantity=2)
        quote = self.quote({str(self.games[0].pk): 3})
        self.assertEqual(quote['total'], Decimal('135'))
        self.assertEqual(quote['cart_items'][0]['price_groups'], [(Decimal('45'), 3)])

    def test_fixed_discount_allocates_every_cent_and_never_exceeds_price(self):
        offer = self.offer(kind='cart_amount', value=Decimal('1'), minimum_quantity=2)
        quote = self.quote({str(self.games[-1].pk): 3})
        self.assertEqual(quote['total'], Decimal('29'))
        self.assertEqual(quote['cart_items'][0]['price_groups'], [(Decimal('9.67'), 2), (Decimal('9.66'), 1)])
        offer.value = 999
        offer.save()
        self.assertEqual(self.quote()['total'], Decimal('0'))

    def test_selected_games_only_count_toward_threshold_and_discount(self):
        offer = self.offer(minimum_quantity=2, apply_to_all=False)
        offer.games.add(self.games[0], self.games[1])
        quote = self.quote()
        self.assertEqual(quote['total'], Decimal('110'))
        self.assertEqual(quote['cart_items'][1]['item_total'], Decimal('0'))
        offer.games.set([self.games[0]])
        quote = self.quote()
        self.assertEqual(quote['total'], Decimal('150'))
        self.assertEqual(quote['cart_offers'][0]['missing'], 1)

    def test_one_free_per_cart_and_repeated_groups_have_distinct_rules(self):
        offer = self.offer()
        cart = {str(game.pk): 2 for game in self.games}
        self.assertEqual(self.quote(cart)['total'], Decimal('290'))
        offer.repeat_free_groups = True
        offer.save()
        quote = self.quote(cart)
        # Sorted groups: 50,50,40,40,30 / 30,20,20,10,10 -> free 30 and 10.
        self.assertEqual(quote['total'], Decimal('260'))

    def test_best_cart_offer_competes_with_individual_discounts_without_stacking(self):
        self.offer()
        item_offer = self.offer(kind='percentage', value=20)
        self.assertEqual(self.quote()['total'], Decimal('120'))
        self.assertIsNone(self.quote()['applied_promotion'])
        self.offer(name='Buy two, 30% off', kind='cart_percentage', value=30, minimum_quantity=2)
        self.assertEqual(self.quote()['total'], Decimal('105'))
        item_offer.delete()
        self.assertEqual(self.quote()['total'], Decimal('105'))

    def test_scheduled_expired_paused_and_unscoped_offers_do_not_apply(self):
        self.offer(is_active=False)
        self.offer(starts_at=timezone.now() + timedelta(days=1))
        self.offer(ends_at=timezone.now() - timedelta(minutes=1))
        self.offer(apply_to_all=False)
        self.assertEqual(self.quote()['total'], Decimal('150'))

    def test_unknown_prices_do_not_count_and_block_checkout(self):
        unknown = BoardGame.objects.create(name='Unknown price', stock_quantity=1)
        self.offer(minimum_quantity=2)
        quote = self.quote({str(self.games[0].pk): 1, str(unknown.pk): 1})
        self.assertFalse(quote['can_checkout'])
        self.assertEqual(quote['cart_offers'][0]['missing'], 1)
        self.assertRedirects(self.checkout({str(self.games[0].pk): 1, str(unknown.pk): 1}), reverse('view_cart'))
        self.assertFalse(StockReservation.objects.exists())

    def test_duplicate_copy_quote_has_exact_totals_and_frozen_promotion(self):
        offer = self.offer()
        self.assertRedirects(self.checkout({str(self.games[0].pk): 5}), reverse('checkout_success'))
        reservations = StockReservation.objects.order_by('quoted_unit_price')
        self.assertEqual(reservations.count(), 2)
        self.assertEqual(list(reservations.values_list('quantity', 'quoted_unit_price')), [(1, Decimal('0')), (4, Decimal('50'))])
        free = reservations.first()
        self.assertIsNotNone(free.quote_group)
        self.assertEqual(free.promotion_snapshot['total'], '200.00')
        offer.delete()
        BoardGame.objects.filter(pk=self.games[0].pk).update(sale_price=100)
        confirm_reserved_sale(free.pk, actor=self.user)
        self.assertEqual(Sale.objects.count(), 2)
        self.assertEqual(sum((sale.total for sale in Sale.objects.all()), Decimal('0')), Decimal('200'))
        self.games[0].refresh_from_db()
        self.assertEqual(self.games[0].stock_quantity, 15)
        self.assertFalse(StockReservation.objects.exclude(status='confirmed').exists())
        with self.assertRaises(ValueError):
            confirm_reserved_sale(free.pk)
        self.assertEqual(ledger_summary()['net_received'], Decimal('0'))
        paid = Sale.objects.get(unit_price=50)
        record_cash(sale=paid, kind='receipt', holder='business', amount=Decimal('200'),
                    date=timezone.localdate(), method='cash', reference='Bundle paid', notes='',
                    request_id=uuid4(), actor=self.user)
        self.assertEqual(ledger_summary()['partner_share'], Decimal('100'))
        self.assertEqual(len(mail.outbox), 0)
        self.assertIn('Discount: €50.00', quote_message(free.customer_quote))
        self.assertIn('Total: €200.00', quote_message(free.customer_quote))
        self.assertIn('Promotion bundle items must be confirmed together.', quote_message(free.customer_quote))

    def test_partial_expiry_or_insufficient_stock_rolls_back_entire_bundle(self):
        self.offer()
        self.checkout()
        free = StockReservation.objects.get(quoted_unit_price=0)
        other = StockReservation.objects.exclude(pk=free.pk).first()
        StockReservation.objects.filter(pk=other.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        with self.assertRaises(ValueError):
            confirm_reserved_sale(free.pk)
        self.assertFalse(Sale.objects.exists())
        StockReservation.objects.update(expires_at=timezone.now() + timedelta(minutes=30))
        BoardGame.objects.filter(pk=other.game_id).update(stock_quantity=0)
        with self.assertRaises(ValueError):
            confirm_reserved_sale(free.pk)
        self.assertFalse(Sale.objects.exists())
        self.assertFalse(StockReservation.objects.exclude(status='active').exists())

    def test_bundle_extension_and_cancellation_affect_all_items(self):
        self.offer()
        self.checkout()
        free = StockReservation.objects.get(quoted_unit_price=0)
        update_reservation(free.pk, minutes=45)
        self.assertEqual(len(set(StockReservation.objects.values_list('expires_at', flat=True))), 1)
        with self.assertRaises(ProtectedError):
            free.game.delete()
        update_reservation(free.pk, cancel=True)
        self.assertFalse(StockReservation.objects.exclude(status='cancelled').exists())
        with self.assertRaises(ValueError):
            confirm_reserved_sale(free.pk)

    def test_admin_form_accepts_mechanics_and_rejects_bad_rules(self):
        data = dict(name='Five for four', kind='cheapest_free', minimum_quantity=5,
                    apply_to_all=True, is_active=True, starts_at='2026-01-01T10:00')
        form = PromotionForm(data)
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.save().value, Decimal('0'))
        for changes in ({'minimum_quantity': 1}, {'minimum_quantity': 101},
                        {'kind': 'cart_percentage', 'value': 101}, {'kind': 'cart_amount', 'value': ''}):
            form = PromotionForm(dict(data, **changes))
            self.assertFalse(form.is_valid())

    def test_cart_product_and_staff_pages_show_mechanic_and_snapshot(self):
        self.offer()
        self.checkout()
        self.client.force_login(self.user)
        reservation = StockReservation.objects.first()
        for name in ('confirm_reservation', 'cancel_reservation', 'extend_reservation'):
            self.assertContains(self.client.get(reverse(name, args=[reservation.pk])), 'every item in this bundle')
        sale = confirm_reserved_sale(reservation.pk, actor=self.user)
        self.assertContains(self.client.get(reverse('sale_detail', args=[sale.pk])), 'Promotion bundle')
        self.assertContains(self.client.get(reverse('promotion_list')), 'Buy 5 eligible copies, pay for 4')
        self.assertContains(self.client.get(reverse('game_detail', args=[self.games[0].pk])), 'Cart offers for this game')
        session = self.client.session
        session['cart'] = {str(game.pk): 1 for game in self.games}
        session.save()
        response = self.client.get(reverse('view_cart'))
        self.assertContains(response, 'Buy five, pay for four')
        self.assertContains(response, '€140.00')

    def test_invalid_or_negative_quantities_never_produce_a_discount(self):
        self.offer()
        for quantity in (-1, 0, 'bad', True, 10001):
            with self.assertRaises(ValueError):
                self.quote({str(self.games[0].pk): quantity})
        self.assertEqual(self.client.get(reverse('add_to_cart', args=[self.games[0].pk])).status_code, 405)
        self.client.post(reverse('add_to_cart', args=[self.games[0].pk]), {'quantity': '-5'})
        self.assertFalse(self.client.session.get('cart'))
