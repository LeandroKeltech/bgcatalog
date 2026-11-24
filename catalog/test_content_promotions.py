import json
import tempfile
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .content import sanitize_description
from .finance import confirm_reserved_sale, update_reservation
from .management.commands.enrich_catalog_content import select_videos
from .models import BoardGame, GameVideo, Promotion, StockReservation, CustomerProfile
from .pricing import with_selling_price


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class PromotionTests(TestCase):
    def setUp(self):
        self.game = BoardGame.objects.create(name='Test game', stock_quantity=3, sale_price=30, msrp_price=40)
        self.other = BoardGame.objects.create(name='Other', stock_quantity=1, msrp_price=25, discount_percentage=10)

    def offer(self, **kwargs):
        values = dict(name='Special offer', kind='percentage', value=Decimal('10'), apply_to_all=True,
                      starts_at=timezone.now() - timedelta(hours=1))
        values.update(kwargs)
        return Promotion.objects.create(**values)

    def assert_prices_match(self, expected):
        for game in with_selling_price(BoardGame.objects.all()):
            self.assertEqual(game.final_price, expected[game.pk])
            self.assertEqual(game.selling_price.quantize(Decimal('.01')), game.final_price)

    def test_percentage_and_legacy_base_prices_match_database_filtering(self):
        self.offer()
        self.assert_prices_match({self.game.pk: Decimal('27'), self.other.pk: Decimal('20.25')})

    def test_best_offer_wins_without_stacking(self):
        self.offer()
        self.offer(kind='amount', value=Decimal('5'))
        self.offer(kind='price', value=Decimal('26'))
        self.assert_prices_match({self.game.pk: Decimal('25'), self.other.pk: Decimal('17.50')})

    def test_scoped_offers_and_zero_prices(self):
        offer = self.offer(apply_to_all=False, kind='amount', value=Decimal('99'))
        offer.games.add(self.game)
        self.assert_prices_match({self.game.pk: Decimal('0'), self.other.pk: Decimal('22.50')})

    def test_paused_scheduled_expired_and_high_offers_are_ignored(self):
        self.offer(is_active=False)
        self.offer(starts_at=timezone.now() + timedelta(days=1))
        self.offer(ends_at=timezone.now() - timedelta(minutes=1))
        self.offer(kind='price', value=Decimal('99'))
        self.assert_prices_match({self.game.pk: Decimal('30'), self.other.pk: Decimal('22.50')})

    def test_unknown_price_stays_unknown(self):
        unknown = BoardGame.objects.create(name='Unknown')
        self.offer(kind='price', value=Decimal('10'))
        game = with_selling_price(BoardGame.objects.all()).get(pk=unknown.pk)
        self.assertIsNone(game.final_price)
        self.assertIsNone(game.selling_price)

    def test_checkout_snapshots_promotion_price_for_confirmation(self):
        self.settings_override = override_settings(WHATSAPP_SHOP_NUMBER='+353891234567')
        self.settings_override.enable()
        self.addCleanup(self.settings_override.disable)
        customer = get_user_model().objects.create_user(username='buyer@example.com', email='buyer@example.com')
        CustomerProfile.objects.create(user=customer, full_name='Buyer', phone='+353891234568')
        self.client.force_login(customer)
        offer = self.offer()
        session = self.client.session
        session['cart'] = {str(self.game.pk): 1}
        session.save()
        response = self.client.post(reverse('checkout'), {
            'customer_name': 'Buyer', 'customer_email': 'buyer@example.com', 'customer_phone': '123',
        })
        self.assertRedirects(response, reverse('checkout_success'))
        reservation = StockReservation.objects.get(game=self.game)
        self.assertEqual(reservation.quoted_unit_price, Decimal('27'))
        offer.is_active = False
        offer.save()
        sale = confirm_reserved_sale(reservation.pk)
        self.assertEqual(sale.unit_price, Decimal('27'))
        with self.assertRaises(ValueError):
            update_reservation(reservation.pk, cancel=True)

    def test_staff_can_create_edit_and_pause_promotions(self):
        self.assertEqual(self.client.get(reverse('promotion_list')).status_code, 302)
        user = get_user_model().objects.create_user(username='staff', is_staff=True)
        user.groups.add(Group.objects.get_or_create(name='admin')[0])
        self.client.force_login(user)
        data = dict(name='Weekend', kind='percentage', value='15', is_active='on',
                    starts_at='2026-01-01T10:00', games=[self.game.pk])
        response = self.client.post(reverse('promotion_new'), data)
        self.assertRedirects(response, reverse('promotion_list'))
        offer = Promotion.objects.get()
        self.assertEqual(list(offer.games.all()), [self.game])
        self.assertContains(self.client.get(reverse('promotion_edit', args=[offer.pk])), 'Save promotion')
        self.assertEqual(self.client.get(reverse('promotion_toggle', args=[offer.pk])).status_code, 405)
        self.client.post(reverse('promotion_toggle', args=[offer.pk]))
        offer.refresh_from_db()
        self.assertFalse(offer.is_active)


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class ContentTests(TestCase):
    def test_external_html_is_sanitized_and_structured(self):
        result = sanitize_description('<h2 onclick="bad()">Play</h2><p>A <strong>great</strong> game.</p>'
                                      '<ul><li>Two players</li></ul><script>alert(1)</script>'
                                      '<img src=x onerror=bad()><a href="javascript:bad()">Bad link</a>'
                                      '<a href="/boardgame/1">Source</a>')
        self.assertIn('<h3>Play</h3>', result)
        self.assertIn('<ul><li>Two players</li></ul>', result)
        self.assertIn('<strong>great</strong>', result)
        for unsafe in ('onclick', 'script', 'alert', '<img', 'javascript:'):
            self.assertNotIn(unsafe, result)
        self.assertIn('https://boardgamegeek.com/boardgame/1', result)

    def test_long_plain_text_becomes_readable_paragraphs(self):
        text = 'This is a complete sentence explaining how to play the game. ' * 25
        self.assertGreater(sanitize_description(text).count('<p>'), 2)
        self.assertNotIn('bad()', sanitize_description('Text<iframe>bad()</iframe>'))

    def test_video_selection_checks_identity_language_visibility_and_duplicates(self):
        good = dict(objectid='123', videohost='youtube', language='English', hidden='0',
                    extvideoid='abcdefghijk', gallery='review')
        instructional = dict(good, extvideoid='12345678901', gallery='instructional')
        payload = {'videos': [good, good, dict(good, objectid='456'), dict(good, language='French'),
                              dict(good, hidden='1'), dict(good, extvideoid='<script>'), instructional]}
        self.assertEqual(select_videos(payload, '123'), [instructional, good])

    def test_cached_import_is_idempotent_and_retains_source(self):
        game = BoardGame.objects.create(name='Game', bgg_id='123', notes='Private inventory note', source_metadata={'bgg_status': 'verified'})
        video = dict(objectid='123', videohost='youtube', language='English', hidden='0',
                     extvideoid='abcdefghijk', gallery='review', title='Review', videoid=42)
        with tempfile.TemporaryDirectory(dir=settings.BASE_DIR) as directory:
            Path(directory, 'bgg-123.json').write_text(json.dumps({'objectid': '123', 'description': '<p>Game <b>rules</b>.</p>'}), encoding='utf-8')
            Path(directory, 'videos-123.json').write_text(json.dumps({'videos': [video]}), encoding='utf-8')
            for _ in range(2):
                call_command('enrich_catalog_content', videos=True, cache_dir=Path(directory), verbosity=0)
        game.refresh_from_db()
        self.assertIn('<b>rules</b>', game.description_html)
        self.assertEqual(GameVideo.objects.count(), 1)
        response = self.client.get(reverse('game_detail', args=[game.pk]))
        self.assertContains(response, 'Review')
        self.assertContains(response, 'Watch on YouTube')
        self.assertNotContains(response, '<iframe')
        self.assertNotContains(response, 'Private inventory note')

    @patch('catalog.management.commands.enrich_catalog_content.requests.Session.get')
    def test_failed_video_refresh_preserves_existing_video(self, get):
        import requests
        get.side_effect = requests.RequestException('Temporary failure')
        game = BoardGame.objects.create(name='Game', bgg_id='123', source_metadata={'bgg_status': 'verified'})
        GameVideo.objects.create(game=game, youtube_id='abcdefghijk', title='Existing', source_url='https://boardgamegeek.com/video/42')
        with tempfile.TemporaryDirectory(dir=settings.BASE_DIR) as directory:
            call_command('enrich_catalog_content', videos=True, cache_dir=Path(directory), verbosity=0)
        self.assertTrue(game.videos.get().is_active)
        game.refresh_from_db()
        self.assertEqual(game.source_metadata['video_status'], 'pending')
