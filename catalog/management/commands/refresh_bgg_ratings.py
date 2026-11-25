"""Refresh verified Geek game ratings from public website statistics."""
import json
import math
import time
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalog.models import BoardGame


def parse_ratings(item):
    stats = item.get('stats')
    if not isinstance(stats, dict):
        raise ValueError('BGG statistics are missing')
    count = int(stats.get('usersrated', 0))
    if count < 0:
        raise ValueError('Invalid BGG rating count')
    result = {
        'rating_average': None,
        'rating_bayes': None,
        'average_weight': None,
        'num_ratings': count,
        'rank_overall': None,
    }
    if count:
        for target, key in [('rating_average', 'average'), ('rating_bayes', 'baverage')]:
            value = stats.get(key)
            if value in (None, '', 'N/A') and target == 'rating_bayes':
                continue
            value = float(value)
            if not math.isfinite(value) or not 0 <= value <= 10:
                raise ValueError('BGG rating is outside 0–10')
            result[target] = value
        weight = stats.get('averageweight')
        if weight not in (None, '', 'N/A'):
            weight = float(weight)
            if not math.isfinite(weight) or not 0 <= weight <= 5:
                raise ValueError('BGG complexity rating is outside 0–5')
            result['average_weight'] = weight or None
        rank = next((row.get('rank') for row in item.get('rankinfo', [])
                     if row.get('browsesubtype') == 'boardgame'), None)
        if str(rank).isdigit() and int(rank) > 0:
            result['rank_overall'] = int(rank)
    return result


class Command(BaseCommand):
    help = 'Refresh average BGG ratings for verified entries; preserves prices, conditions and click counts.'

    def add_arguments(self, parser):
        parser.add_argument('--refresh', action='store_true')
        parser.add_argument('--cache-dir', type=Path, default=settings.BASE_DIR / '.catalog-import')

    def handle(self, *args, **options):
        cache = options['cache_dir']
        cache.mkdir(parents=True, exist_ok=True)
        session = requests.Session()
        session.headers['User-Agent'] = 'BG-Catalog/1.0 (personal inventory catalog)'
        fetched, updated, unrated, errors = {}, 0, 0, 0
        for game in BoardGame.objects.filter(source_metadata__bgg_status='verified').order_by('pk'):
            try:
                if not game.bgg_id or not game.bgg_id.isdigit():
                    raise ValueError('Verified numeric BGG identity required')
                if game.bgg_id not in fetched:
                    path = cache / f'bgg-stats-{game.bgg_id}.json'
                    if path.exists() and not options['refresh']:
                        payload = json.loads(path.read_text(encoding='utf-8'))
                    else:
                        time.sleep(.4)
                        response = session.get('https://api.geekdo.com/api/dynamicinfo', params={
                            'objecttype': 'thing', 'objectid': game.bgg_id,
                        }, timeout=25)
                        response.raise_for_status()
                        item = response.json()['item']
                        parse_ratings(item)
                        payload = {'objectid': game.bgg_id, 'fetched_at': timezone.now().isoformat(), 'item': item}
                        path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
                    if payload['objectid'] != game.bgg_id:
                        raise ValueError('Cached statistics do not match the requested BGG ID')
                    fetched[game.bgg_id] = payload
                payload = fetched[game.bgg_id]
                values = parse_ratings(payload['item'])
                # Update metadata under current state, so staff edits are retained.
                with transaction.atomic():
                    current = BoardGame.objects.select_for_update().get(pk=game.pk)
                    if current.bgg_id != game.bgg_id:
                        raise ValueError('Game identity changed while retrieving ratings')
                    for key, value in values.items():
                        setattr(current, key, value)
                    metadata = dict(current.source_metadata)
                    metadata.update(bgg_rating_status='verified' if values['rating_average'] is not None else 'unrated',
                                    bgg_rating_checked_at=payload['fetched_at'],
                                    bgg_rating_source=f'https://boardgamegeek.com/thing/{game.bgg_id}')
                    metadata.pop('bgg_rating_error', None)
                    current.source_metadata = metadata
                    current.save(update_fields=[*values, 'source_metadata'])
                updated += 1
                unrated += values['rating_average'] is None
            except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                errors += 1
                self.stderr.write(f'{game.name}: {exc}')
        self.stdout.write(self.style.SUCCESS(f'Updated {updated} entries; unrated: {unrated}; errors: {errors}.'))
