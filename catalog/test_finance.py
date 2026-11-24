import csv
import uuid
from datetime import timedelta
from decimal import Decimal
from io import StringIO

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models.deletion import ProtectedError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .finance import ledger_summary, record_cash, record_sale, record_transfer
from .models import BoardGame, CashEntry, PartnerTransfer, Sale, StockReservation


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class FinanceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='staff', is_staff=True)
        self.user.groups.add(Group.objects.get_or_create(name='admin')[0])
        self.game = BoardGame.objects.create(name='Test game', stock_quantity=5, msrp_price=40, sale_price=30)
        self.client.force_login(self.user)

    def sale(self, **kwargs):
        values = dict(game=self.game, quantity=1, unit_price=Decimal('30'), customer_name='Buyer',
                      reference='Test sale', sale_date=timezone.localdate(), deduct_stock=True,
                      request_id=uuid.uuid4(), actor=self.user)
        values.update(kwargs)
        return record_sale(**values)

    def cash(self, sale, amount='30', kind='receipt', holder='business', **kwargs):
        values = dict(sale=sale, amount=Decimal(amount), kind=kind, holder=holder,
                      date=timezone.localdate(), method='cash', reference='', notes='',
                      request_id=uuid.uuid4(), actor=self.user)
        values.update(kwargs)
        return record_cash(**values)

    def transfer(self, amount, direction='to_partner', **kwargs):
        values = dict(amount=Decimal(amount), direction=direction, date=timezone.localdate(),
                      reference='Bank reference', notes='', request_id=uuid.uuid4(), actor=self.user)
        values.update(kwargs)
        return record_transfer(**values)

    def test_sale_reduces_stock_without_inventing_payment(self):
        sale = self.sale(quantity=2)
        self.game.refresh_from_db()
        self.assertEqual(self.game.stock_quantity, 3)
        self.assertEqual(sale.outstanding, Decimal('60'))
        self.assertEqual(ledger_summary()['net_received'], Decimal('0'))

    def test_sale_price_and_name_are_snapshots(self):
        sale = self.sale()
        BoardGame.objects.filter(pk=self.game.pk).update(name='Renamed', sale_price=99)
        sale.refresh_from_db()
        self.assertEqual(sale.game_name, 'Test game')
        self.assertEqual(sale.total, Decimal('30'))

    def test_partial_receipts_only_split_actual_cash(self):
        sale = self.sale()
        self.cash(sale, '10')
        self.assertEqual(sale.outstanding, Decimal('20'))
        self.assertEqual(ledger_summary()['owed_to_partner'], Decimal('5'))
        self.cash(sale, '20')
        self.assertEqual(sale.outstanding, Decimal('0'))
        self.assertEqual(ledger_summary()['owed_to_partner'], Decimal('15'))

    def test_refunds_reduce_share_and_preserve_stock(self):
        sale = self.sale()
        self.cash(sale)
        self.cash(sale, '10', kind='refund')
        summary = ledger_summary()
        self.assertEqual(summary['net_received'], Decimal('20'))
        self.assertEqual(summary['owed_to_partner'], Decimal('10'))
        self.game.refresh_from_db()
        self.assertEqual(self.game.stock_quantity, 4)

    def test_partner_direct_receipts_are_credited(self):
        sale = self.sale()
        self.cash(sale, holder='partner')
        self.assertEqual(ledger_summary()['owed_by_partner'], Decimal('15'))
        self.transfer('15', direction='from_partner')
        self.assertEqual(ledger_summary()['partner_balance'], Decimal('0'))

    def test_partner_payout_and_refund_can_create_credit(self):
        sale = self.sale()
        self.cash(sale)
        self.transfer('15')
        self.assertEqual(ledger_summary()['partner_balance'], Decimal('0'))
        self.cash(sale, '10', kind='refund')
        self.assertEqual(ledger_summary()['owed_by_partner'], Decimal('5'))

    def test_overpayments_refunds_and_transfers_are_rejected(self):
        sale = self.sale()
        with self.assertRaises(ValueError):
            self.cash(sale, '31')
        with self.assertRaises(ValueError):
            self.cash(sale, '1', kind='refund')
        self.cash(sale)
        with self.assertRaises(ValueError):
            self.transfer('15.01')
        with self.assertRaises(ValueError):
            self.cash(sale, '30.01', kind='refund')

    def test_cent_rounding_is_applied_to_total_not_each_receipt(self):
        sale = self.sale(unit_price=Decimal('0.02'))
        self.cash(sale, '0.01')
        self.cash(sale, '0.01')
        self.assertEqual(ledger_summary()['partner_share'], Decimal('0.01'))
        self.assertEqual(ledger_summary()['business_share'], Decimal('0.01'))

    def test_repeated_post_tokens_do_not_duplicate_financial_effects(self):
        key = uuid.uuid4()
        sale = self.sale(request_id=key)
        self.assertEqual(self.sale(request_id=key).pk, sale.pk)
        key = uuid.uuid4()
        entry = self.cash(sale, request_id=key)
        self.assertEqual(self.cash(sale, request_id=key).pk, entry.pk)
        key = uuid.uuid4()
        transfer = self.transfer('15', request_id=key)
        self.assertEqual(self.transfer('15', request_id=key).pk, transfer.pk)
        self.assertEqual(Sale.objects.count(), 1)
        self.assertEqual(CashEntry.objects.count(), 1)
        self.assertEqual(PartnerTransfer.objects.count(), 1)
        self.game.refresh_from_db()
        self.assertEqual(self.game.stock_quantity, 4)

    def test_historical_sale_does_not_deduct_stock_twice(self):
        self.sale(deduct_stock=False)
        self.game.refresh_from_db()
        self.assertEqual(self.game.stock_quantity, 5)

    def test_sale_cannot_consume_reserved_stock(self):
        StockReservation.objects.create(game=self.game, quantity=5, customer_name='Buyer',
                                        customer_email='buyer@example.com', session_key='test')
        with self.assertRaises(ValueError):
            self.sale()
        self.assertFalse(Sale.objects.exists())

    def test_last_copy_marks_game_sold_out_and_history_is_protected(self):
        self.sale(quantity=5)
        self.game.refresh_from_db()
        self.assertEqual(self.game.stock_quantity, 0)
        self.assertTrue(self.game.is_sold)
        with self.assertRaises(ProtectedError):
            self.game.delete()

    def test_confirmation_creates_one_unpaid_sale_and_rejects_repeat(self):
        reservation = StockReservation.objects.create(game=self.game, quantity=2,
            customer_name='Buyer', customer_email='buyer@example.com', session_key='test')
        sale = reservation.confirm()
        self.assertEqual(sale.total, Decimal('60'))
        self.assertEqual(sale.received, Decimal('0'))
        with self.assertRaises(ValueError):
            reservation.confirm()
        self.game.refresh_from_db()
        self.assertEqual(self.game.stock_quantity, 3)

    def test_expired_reservation_cannot_become_sale(self):
        reservation = StockReservation.objects.create(game=self.game, quantity=1,
            customer_name='Buyer', customer_email='buyer@example.com', session_key='test',
            expires_at=timezone.now() - timedelta(seconds=1))
        with self.assertRaises(ValueError):
            reservation.confirm()
        self.assertFalse(Sale.objects.exists())

    def test_staff_pages_render_and_csv_is_safe(self):
        sale = self.sale(customer_name='=FORMULA()', reference='Safe')
        self.cash(sale)
        for name, args in [('admin_panel', []), ('new_game', []), ('edit_game', [self.game.pk]),
                           ('finance_dashboard', []), ('new_sale', []), ('sale_detail', [sale.pk]),
                           ('partner_transfer', [])]:
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200)
        response = self.client.get(reverse('finance_export'))
        rows = list(csv.reader(StringIO(response.content.decode())))
        self.assertEqual(rows[1][4], "'=FORMULA()")
        self.assertContains(response, '15.00')

    def test_finance_pages_and_mutations_require_staff(self):
        sale = self.sale()
        self.client.logout()
        for name, args in [('finance_dashboard', []), ('finance_export', []), ('sale_detail', [sale.pk]),
                           ('new_sale', []), ('partner_transfer', [])]:
            self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 302)
        self.assertEqual(self.client.post(reverse('sale_detail', args=[sale.pk]), {}).status_code, 302)
        self.assertFalse(CashEntry.objects.exists())

    def test_inventory_form_marks_sold_out_and_restocked(self):
        values = {'name': self.game.name, 'stock_quantity': 0, 'condition': 'new', 'msrp_price': '40', 'sale_price': '30'}
        self.assertEqual(self.client.post(reverse('edit_game', args=[self.game.pk]), values).status_code, 302)
        self.game.refresh_from_db()
        self.assertTrue(self.game.is_sold)
        values['stock_quantity'] = 2
        self.client.post(reverse('edit_game', args=[self.game.pk]), values)
        self.game.refresh_from_db()
        self.assertFalse(self.game.is_sold)

    def test_catalog_includes_sold_out_and_can_filter(self):
        sold = BoardGame.objects.create(name='Sold game', stock_quantity=0, is_sold=True)
        self.assertContains(self.client.get(reverse('catalog')), 'Sold game')
        response = self.client.get(reverse('catalog'), {'availability': 'sold_out'})
        self.assertEqual(list(response.context['games']), [sold])
        response = self.client.get(reverse('catalog'), {'availability': 'available'})
        self.assertEqual(list(response.context['games']), [self.game])
