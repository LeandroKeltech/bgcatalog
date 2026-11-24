import json
import tempfile
from decimal import Decimal
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from .condition_pricing import condition_price
from .models import BoardGame, StockReservation


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class ConditionPricingTests(TestCase):
    def test_condition_prices_round_to_cents(self):
        for condition, expected in [('new', '13.99'), ('like_new', '11.99'), ('used', '8.00')]:
            self.assertEqual(condition_price(Decimal('19.99'), condition), Decimal(expected))
        self.assertIsNone(condition_price(None, 'new'))
        self.assertEqual(condition_price(Decimal('0'), 'new'), Decimal('0'))

    def test_repricing_is_explicit_audited_idempotent_and_keeps_existing_quotes(self):
        game = BoardGame.objects.create(name='Used game', condition='used', msrp_price=Decimal('39.99'),
                                        sale_price=Decimal('29.99'), stock_quantity=5)
        unknown = BoardGame.objects.create(name='Unknown reference', sale_price=Decimal('15'))
        reservation = StockReservation.objects.create(game=game, quantity=1, quoted_unit_price=Decimal('29.99'),
            customer_name='Buyer', customer_email='buyer@example.com', session_key='test')
        with tempfile.TemporaryDirectory(dir=settings.BASE_DIR) as directory:
            options = dict(backup_dir=Path(directory), stdout=StringIO())
            call_command('reprice_inventory', **options)
            game.refresh_from_db()
            self.assertEqual(game.sale_price, Decimal('29.99'))
            self.assertFalse(list(Path(directory).glob('*.json')))
            call_command('reprice_inventory', apply=True, **options)
            game.refresh_from_db()
            self.assertEqual(game.sale_price, Decimal('16.00'))
            self.assertEqual(game.discount_percentage, 60)
            self.assertEqual(game.source_metadata['pricing_override']['condition'], 'used')
            backups = list(Path(directory).glob('*.json'))
            self.assertEqual(len(backups), 1)
            backup = json.loads(backups[0].read_text(encoding='utf-8'))
            self.assertEqual(backup['games'][0]['sale_price'], '29.99')
            call_command('reprice_inventory', apply=True, **options)
            self.assertEqual(len(list(Path(directory).glob('*.json'))), 1)
        unknown.refresh_from_db()
        self.assertEqual(unknown.sale_price, Decimal('15'))
        reservation.refresh_from_db()
        self.assertEqual(reservation.quoted_unit_price, Decimal('29.99'))
        self.assertEqual(game.stock_quantity, 5)

    def test_staff_can_filter_all_non_new_or_one_condition(self):
        user = get_user_model().objects.create_user(username='staff', is_staff=True)
        user.groups.add(Group.objects.get_or_create(name='admin')[0])
        self.client.force_login(user)
        BoardGame.objects.create(name='New copy', condition='new')
        used = BoardGame.objects.create(name='Used copy', condition='used')
        like_new = BoardGame.objects.create(name='Like new copy', condition='like_new')
        response = self.client.get(reverse('admin_panel'), {'condition': 'not_new', 'per_page': '100'})
        self.assertEqual(list(response.context['games']), [like_new, used])
        self.assertContains(response, 'value="not_new" selected')
        response = self.client.get(reverse('admin_panel'), {'condition': 'used', 'search': 'Used'})
        self.assertEqual(list(response.context['games']), [used])
