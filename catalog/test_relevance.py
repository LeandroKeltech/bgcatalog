import json
import tempfile
from datetime import timedelta
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .engagement import CLICK_WINDOW_SECONDS
from .management.commands.refresh_bgg_ratings import parse_ratings
from .models import BoardGame, StockReservation


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class RelevanceTests(TestCase):
    def test_default_sort_is_clicks_then_average_rating_then_id(self):
        unknown = BoardGame.objects.create(name='Unknown rating', click_count=3)
        low = BoardGame.objects.create(name='Low rating', click_count=3, rating_average=6)
        high = BoardGame.objects.create(name='High rating', click_count=3, rating_average=9)
        tied = BoardGame.objects.create(name='Another high', click_count=3, rating_average=9)
        popular = BoardGame.objects.create(name='Most clicked', click_count=4, rating_average=5)
        for params in ({}, {'sort': 'relevance'}, {'sort': 'invalid'}):
            response = self.client.get(reverse('catalog'), params)
            self.assertEqual(list(response.context['games']), [popular, high, tied, low, unknown])
            self.assertEqual(response.context['sort_by'], 'relevance')
            self.assertContains(response, 'value="relevance" selected')
        response = self.client.get(reverse('catalog'), {'sort': 'name'})
        self.assertEqual(list(response.context['games']), [tied, high, low, popular, unknown])

    def test_default_sort_places_sold_out_games_last_before_pagination(self):
        sold = BoardGame.objects.create(name='Sold', is_sold=True, click_count=100)
        zero_stock = BoardGame.objects.create(name='Zero stock', stock_quantity=0, click_count=99)
        available = BoardGame.objects.bulk_create([
            BoardGame(name=f'Available {i:02}', click_count=i) for i in range(25)
        ])
        expected = list(reversed(available)) + [sold, zero_stock]
        for params in ({}, {'sort': 'relevance'}, {'sort': 'invalid'}):
            with self.subTest(params=params):
                first = self.client.get(reverse('catalog'), params)
                second = self.client.get(reverse('catalog'), {**params, 'page': 2})
                self.assertEqual(list(first.context['games']), expected[:24])
                self.assertEqual(list(second.context['games']), expected[24:])
        response = self.client.get(reverse('catalog'), {'availability': 'sold_out'})
        self.assertEqual(list(response.context['games']), [sold, zero_stock])

    def test_all_sort_options_put_fully_reserved_and_sold_out_games_last(self):
        reserved = BoardGame.objects.create(name='A reserved', click_count=100, sale_price=1)
        sold = BoardGame.objects.create(name='B sold', is_sold=True, click_count=99, sale_price=2)
        zero = BoardGame.objects.create(name='C zero', stock_quantity=0, sale_price=3)
        partial = BoardGame.objects.create(name='Partial', stock_quantity=3, sale_price=20)
        expired = BoardGame.objects.create(name='Expired hold', sale_price=30)
        cancelled = BoardGame.objects.create(name='Cancelled hold', sale_price=40)
        for game, quantity, status, expires_at in (
            (reserved, 1, 'active', timezone.now() + timedelta(hours=1)),
            (partial, 1, 'active', timezone.now() + timedelta(hours=1)),
            (partial, 1, 'active', timezone.now() + timedelta(hours=1)),
            (expired, 1, 'active', timezone.now() - timedelta(hours=1)),
            (cancelled, 1, 'cancelled', timezone.now() + timedelta(hours=1)),
        ):
            StockReservation.objects.create(game=game, quantity=quantity, status=status, expires_at=expires_at)
        for sort in ('relevance', 'name', '-name', 'selling_price', '-selling_price', '-created_at', 'year_published'):
            with self.subTest(sort=sort):
                response = self.client.get(reverse('catalog'), {'sort': sort})
                games = list(response.context['games'])
                self.assertEqual(set(games[:3]), {partial, expired, cancelled})
                self.assertEqual(set(games[3:]), {reserved, sold, zero})

    def test_clicks_are_counted_atomically_once_per_session_per_window(self):
        game = BoardGame.objects.create(name='Game')
        detail = reverse('game_detail', args=[game.pk])
        self.client.get(detail)
        self.client.get(detail)
        self.client.get(reverse('catalog'))
        game.refresh_from_db()
        self.assertEqual(game.click_count, 1)
        Client().get(detail)
        game.refresh_from_db()
        self.assertEqual(game.click_count, 2)
        session = self.client.session
        session['recent_product_clicks'] = {str(game.pk): timezone.now().timestamp() - CLICK_WINDOW_SECONDS - 1}
        session.save()
        self.client.get(detail)
        game.refresh_from_db()
        self.assertEqual(game.click_count, 3)

    def test_staff_prefetch_head_and_missing_games_do_not_add_clicks(self):
        game = BoardGame.objects.create(name='Game')
        detail = reverse('game_detail', args=[game.pk])
        self.client.head(detail)
        self.client.get(detail, HTTP_SEC_PURPOSE='prefetch')
        self.client.get(detail, HTTP_PURPOSE='prefetch')
        user = get_user_model().objects.create_user(username='staff', is_staff=True)
        self.client.force_login(user)
        self.client.get(detail)
        self.assertEqual(self.client.get(reverse('game_detail', args=[99999])).status_code, 404)
        game.refresh_from_db()
        self.assertEqual(game.click_count, 0)

    def test_filters_and_pagination_preserve_relevance(self):
        games = [BoardGame(name=f'Collection {i}', condition='used', click_count=i, rating_average=8)
                 for i in range(26)]
        BoardGame.objects.bulk_create(games)
        BoardGame.objects.create(name='Not eligible', condition='new', click_count=100)
        response = self.client.get(reverse('catalog'), {'search': 'Collection', 'condition': 'used', 'page': 2})
        self.assertEqual([g.click_count for g in response.context['games']], [1, 0])
        self.assertEqual(response.context['sort_by'], 'relevance')
        self.assertContains(response, 'condition=used')


class BggRatingsTests(TestCase):
    def test_rating_validation_and_unrated_entries(self):
        result = parse_ratings({'stats': {'usersrated': '42', 'average': '8.125', 'baverage': '7.2'},
                                'rankinfo': [{'browsesubtype': 'boardgame', 'rank': '12'}]})
        self.assertEqual(result['rating_average'], 8.125)
        self.assertEqual(result['rank_overall'], 12)
        self.assertIsNone(parse_ratings({'stats': {'usersrated': '0', 'average': '0'}})['rating_average'])
        for value in ('NaN', 'Infinity', '-1', '11'):
            with self.assertRaises(ValueError):
                parse_ratings({'stats': {'usersrated': 3, 'average': value}})

    def test_cache_refresh_preserves_prices_conditions_and_clicks(self):
        game = BoardGame.objects.create(name='Game', bgg_id='123', condition='used', sale_price=16,
                                        click_count=12, source_metadata={'bgg_status': 'verified', 'manual': 'preserved'})
        with tempfile.TemporaryDirectory(dir=settings.BASE_DIR) as directory:
            payload = {'objectid': '123', 'fetched_at': timezone.now().isoformat(),
                       'item': {'stats': {'usersrated': '42', 'average': '8.125', 'baverage': '7.2'}}}
            Path(directory, 'bgg-stats-123.json').write_text(json.dumps(payload), encoding='utf-8')
            call_command('refresh_bgg_ratings', cache_dir=Path(directory), stdout=StringIO())
        game.refresh_from_db()
        self.assertEqual(game.rating_average, 8.125)
        self.assertEqual(game.num_ratings, 42)
        self.assertEqual(game.sale_price, 16)
        self.assertEqual(game.condition, 'used')
        self.assertEqual(game.click_count, 12)
        self.assertEqual(game.source_metadata['manual'], 'preserved')

    def test_bad_cached_identity_does_not_overwrite_existing_rating(self):
        game = BoardGame.objects.create(name='Game', bgg_id='123', rating_average=8,
                                        source_metadata={'bgg_status': 'verified'})
        with tempfile.TemporaryDirectory(dir=settings.BASE_DIR) as directory:
            Path(directory, 'bgg-stats-123.json').write_text(json.dumps({'objectid': '999'}), encoding='utf-8')
            call_command('refresh_bgg_ratings', cache_dir=Path(directory), stdout=StringIO(), stderr=StringIO())
        game.refresh_from_db()
        self.assertEqual(game.rating_average, 8)
