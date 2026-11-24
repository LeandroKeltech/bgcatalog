from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import BoardGame, StockReservation, CustomerProfile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.conf import settings
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import json


class PricingTests(TestCase):
    def test_explicit_sheet_price_overrides_discount(self):
        game = BoardGame(msrp_price=Decimal('34.99'), sale_price=Decimal('26.24'))
        self.assertEqual(game.final_price, Decimal('26.24'))

    def test_discount_uses_decimal_and_rounds_cents(self):
        game = BoardGame(msrp_price=Decimal('19.99'), discount_percentage=15)
        self.assertEqual(game.final_price, Decimal('16.99'))

    def test_free_and_missing_prices_are_distinct(self):
        self.assertEqual(BoardGame(msrp_price=Decimal('0')).final_price, Decimal('0.00'))
        self.assertIsNone(BoardGame().final_price)


class DatabaseConstraintTests(TestCase):
    def test_invalid_inventory_and_prices_are_rejected(self):
        for values in (
            {'stock_quantity': -1},
            {'msrp_price': Decimal('-0.01')},
            {'sale_price': Decimal('-0.01')},
            {'discount_percentage': -1},
            {'discount_percentage': 101},
        ):
            with self.subTest(values=values):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    BoardGame.objects.create(name='Invalid game', **values)

    def test_invalid_reservation_quantities_and_status_are_rejected(self):
        game = BoardGame.objects.create(name='Test game')
        for values in ({'quantity': 0}, {'quantity': -1}, {'status': 'unknown'}):
            with self.subTest(values=values):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    StockReservation.objects.create(
                        game=game, customer_name='Test Customer',
                        customer_email='customer@example.com', session_key='test', **values
                    )

    def test_active_reservations_reduce_availability(self):
        game = BoardGame.objects.create(name='Test game', stock_quantity=3)
        reservation = StockReservation.objects.create(
            game=game, quantity=2, customer_name='Test Customer',
            customer_email='customer@example.com', session_key='test',
        )
        self.assertEqual(game.available_quantity, 1)
        reservation.cancel()
        self.assertEqual(game.available_quantity, 3)


@override_settings(STORAGES={
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class CatalogFlowTests(TestCase):
    def test_original_and_selling_prices_show_actual_savings(self):
        game = BoardGame.objects.create(name='Price comparison', msrp_price=Decimal('40.00'),
                                        sale_price=Decimal('25.00'), discount_percentage=0)
        for url in (reverse('public_catalog'), reverse('game_detail', args=[game.pk])):
            response = self.client.get(url)
            for text in ('Original price', 'Our price', '€40.00', '€25.00', 'Save €15.00'):
                self.assertContains(response, text)

    def test_price_filters_use_selling_price_instead_of_msrp(self):
        bargain = BoardGame.objects.create(name='Bargain', msrp_price=100, sale_price=10)
        BoardGame.objects.create(name='Higher selling price', msrp_price=5, sale_price=20)
        response = self.client.get(reverse('public_catalog'), {'max_price': '11'})
        self.assertEqual(list(response.context['games']), [bargain])

    def test_calculated_price_filter_preserves_fractional_cents_rounding(self):
        game = BoardGame.objects.create(name='Discounted', msrp_price=19, discount_percentage=15)
        response = self.client.get(reverse('public_catalog'), {'min_price': '16.15', 'max_price': '16.15'})
        self.assertEqual(list(response.context['games']), [game])

    def test_price_sort_uses_selling_price_and_puts_unpriced_games_last(self):
        low = BoardGame.objects.create(name='Low', msrp_price=100, sale_price=5)
        high = BoardGame.objects.create(name='High', msrp_price=10, sale_price=8)
        unknown = BoardGame.objects.create(name='Unknown')
        response = self.client.get(reverse('public_catalog'), {'sort': 'selling_price'})
        self.assertEqual(list(response.context['games']), [low, high, unknown])
        response = self.client.get(reverse('public_catalog'), {'sort': '-selling_price'})
        self.assertEqual(list(response.context['games']), [high, low, unknown])

    def test_catalog_pagination_preserves_search(self):
        BoardGame.objects.bulk_create([BoardGame(name=f'Collection {i}') for i in range(25)])
        response = self.client.get(reverse('public_catalog'), {'search': 'Collection', 'page': '2'})
        self.assertEqual(len(response.context['games']), 1)
        self.assertContains(response, 'Page 2 of 2')
        self.assertContains(response, 'search=Collection&amp;page=1')

    def test_zero_price_is_displayed_and_savings_are_not_fabricated(self):
        game = BoardGame.objects.create(name='Free game', msrp_price=0, sale_price=0)
        response = self.client.get(reverse('game_detail', args=[game.pk]))
        self.assertContains(response, '€0.00', count=2)
        self.assertNotContains(response, 'Save €')
        game.msrp_price = Decimal('5.00')
        game.sale_price = Decimal('10.00')
        self.assertIsNone(game.savings)

    def test_unpriced_game_cannot_create_checkout_reservations(self):
        customer = get_user_model().objects.create_user(username='customer@example.com', email='customer@example.com')
        CustomerProfile.objects.create(user=customer, full_name='Customer', phone='+353891234568')
        self.client.force_login(customer)
        game = BoardGame.objects.create(name='Price pending')
        session = self.client.session
        session['cart'] = {str(game.pk): 1}
        session.save()
        response = self.client.post(reverse('checkout'), {
            'customer_name': 'Customer', 'customer_email': 'customer@example.com',
        })
        self.assertRedirects(response, reverse('view_cart'))
        self.assertFalse(StockReservation.objects.exists())
        self.assertEqual(self.client.session['cart'], {str(game.pk): 1})

    def test_priced_game_renders_in_catalog_and_detail(self):
        game = BoardGame.objects.create(name='Test game', msrp_price=Decimal('25.00'))
        self.assertContains(self.client.get(reverse('public_catalog')), game.name)
        self.assertContains(self.client.get(reverse('game_detail', args=[game.pk])), game.name)

    def test_staff_can_import_a_game(self):
        user = get_user_model().objects.create_user(username='staff', is_staff=True)
        user.groups.add(Group.objects.get_or_create(name='admin')[0])
        self.client.force_login(user)
        response = self.client.post(reverse('import_from_bgg', args=['123']), {
            'name': 'Imported game', 'msrp_price': '29.99', 'stock_quantity': '2',
        })
        self.assertEqual(response.status_code, 302)
        game = BoardGame.objects.get(bgg_id='123')
        self.assertEqual(game.msrp_price, Decimal('29.99'))
        self.assertEqual(game.stock_quantity, 2)


class SheetImportTests(TestCase):
    def run_import(self, rows, enrich=False, mappings=None):
        with TemporaryDirectory(dir=settings.BASE_DIR, prefix='.catalog-import-test-') as directory:
            path = Path(directory) / 'sheet.json'
            path.write_text(json.dumps({
                'spreadsheet_id': 'test-sheet', 'sheet_name': 'Inventory',
                'values': [['Name', 'BGG Link', 'Price', 'id', 'MSRP (€)', 'State', 'balance', 'status'], *rows],
            }), encoding='utf-8')
            kwargs = {}
            if mappings is not None:
                mapping_path = Path(directory) / 'mappings.json'
                mapping_path.write_text(json.dumps({'spreadsheet_id': 'test-sheet', 'mappings': mappings}))
                kwargs['mappings'] = mapping_path
            call_command('import_sheet_catalog', source=path, cache_dir=Path(directory),
                         enrich=enrich, stdout=StringIO(), **kwargs)

    def test_source_ids_preserve_duplicate_titles_and_remaining_stock(self):
        self.run_import([
            ['Test game', 'https://boardgamegeek.com/boardgame/123/test', 15, 1, 20, 'new', 2, 'Available'],
            ['Test game', 'https://boardgamegeek.com/boardgame/123/test', 10, 2, 20, 'used', 0, 'SOLD OUT'],
        ])
        self.assertEqual(BoardGame.objects.count(), 2)
        self.assertEqual(BoardGame.objects.get(source_key='test-sheet:1').stock_quantity, 2)
        self.assertTrue(BoardGame.objects.get(source_key='test-sheet:2').is_sold)

    def test_reimport_does_not_reset_inventory_or_manual_edits(self):
        rows = [['Game', '', 15, 1, 20, 'new', 2, 'Available']]
        self.run_import(rows)
        BoardGame.objects.update(stock_quantity=1, name='Manually edited')
        self.run_import(rows)
        self.assertEqual(BoardGame.objects.count(), 1)
        game = BoardGame.objects.get()
        self.assertEqual(game.stock_quantity, 1)
        self.assertEqual(game.name, 'Manually edited')

    def test_formula_error_is_not_imported_as_zero_price(self):
        self.run_import([['Hum It!', '', '#VALUE!', 1, '€', 'new', 1, 'Available']])
        self.assertIsNone(BoardGame.objects.get().final_price)

    def test_invalid_stock_prevents_partial_import(self):
        with self.assertRaises(CommandError):
            self.run_import([
                ['Valid', '', 15, 1, 20, 'new', 1, 'Available'],
                ['Invalid', '', 15, 2, 20, 'new', -1, 'Available'],
            ])
        self.assertFalse(BoardGame.objects.exists())

    @patch('catalog.management.commands.import_sheet_catalog.Command.fetch_item')
    @patch('catalog.management.commands.import_sheet_catalog.Command.validate_image')
    def test_verified_bgg_content_is_applied(self, validate_image, fetch_item):
        fetch_item.return_value = {
            'name': 'Game', 'description': '<p>Verified English description.</p>',
            'images': {'original': 'https://cf.geekdo-images.com/cover.jpg'},
        }
        self.run_import([['Game', 'https://boardgamegeek.com/boardgame/123/game',
                          15, 1, 20, 'new', 1, 'Available']], enrich=True)
        game = BoardGame.objects.get()
        self.assertEqual(game.description, 'Verified English description.')
        self.assertEqual(game.bgg_id, '123')
        self.assertEqual(game.source_metadata['bgg_status'], 'verified')
        self.assertEqual(validate_image.call_count, 2)

    @patch('catalog.management.commands.import_sheet_catalog.Command.fetch_item')
    def test_mismatched_bgg_identity_does_not_attach_content(self, fetch_item):
        fetch_item.return_value = {'name': 'Different game', 'description': 'Wrong description'}
        self.run_import([['Game', 'https://boardgamegeek.com/boardgame/123/game',
                          15, 1, 20, 'new', 1, 'Available']], enrich=True)
        game = BoardGame.objects.get()
        self.assertIsNone(game.bgg_id)
        self.assertEqual(game.image_url, '')
        self.assertEqual(game.source_metadata['bgg_status'], 'pending')

    def test_only_bgg_hosts_supply_candidate_ids(self):
        from catalog.management.commands.import_sheet_catalog import bgg_id_from_url
        self.assertIsNone(bgg_id_from_url('https://example.com/boardgame/123/game'))
        self.assertEqual(bgg_id_from_url('https://boardgamegeek.com/boardgameexpansion/123/game'), '123')

    def test_image_validation_rejects_external_hosts_before_request(self):
        from catalog.management.commands.import_sheet_catalog import Command
        with self.assertRaises(ValueError):
            Command().validate_image(None, 'https://example.com/cover.jpg')

    @patch('catalog.management.commands.import_sheet_catalog.Command.fetch_item')
    @patch('catalog.management.commands.import_sheet_catalog.Command.validate_image')
    def test_specific_edition_artwork_is_validated_against_parent(self, validate_image, fetch_item):
        fetch_item.side_effect = [
            {'name': 'Game', 'description': 'English description.'},
            {'name': 'Kids edition', 'images': {'original': 'https://cf.geekdo-images.com/kids.jpg'},
             'links': {'boardgame': [{'objectid': '123'}]}},
        ]
        self.run_import([['Game Kids', '', 15, 1, 20, 'new', 1, 'Available']], enrich=True, mappings={
            '1': {'bgg_id': '123', 'expected_name': 'Game', 'version_id': '456', 'version_name': 'Kids edition'},
        })
        game = BoardGame.objects.get()
        self.assertEqual(game.image_url, 'https://cf.geekdo-images.com/kids.jpg')
        self.assertEqual(game.source_metadata['bgg_version_id'], '456')

    @patch('catalog.management.commands.import_sheet_catalog.Command.fetch_item')
    def test_reviewed_mapping_must_still_match_bgg_name(self, fetch_item):
        fetch_item.return_value = {'name': 'Unrelated game'}
        self.run_import([['Game', '', 15, 1, 20, 'new', 1, 'Available']], enrich=True, mappings={
            '1': {'bgg_id': '123', 'expected_name': 'Game'},
        })
        self.assertEqual(BoardGame.objects.get().source_metadata['bgg_status'], 'pending')
