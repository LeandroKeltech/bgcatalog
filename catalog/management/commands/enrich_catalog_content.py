"""Format cached BGG descriptions and import associated English videos."""
import json
import re
import time
from pathlib import Path

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalog.content import sanitize_description
from catalog.models import BoardGame, GameVideo


def select_videos(payload, object_id, limit=2):
    selected, seen = [], set()
    videos = payload.get('videos', [])
    priority = {'instructional': 0, 'instruction': 0, 'review': 1, 'session': 2}
    for video in sorted(videos, key=lambda v: priority.get(v.get('gallery'), 3)):
        external_id = video.get('extvideoid', '')
        if (str(video.get('objectid')) != str(object_id) or video.get('videohost') != 'youtube'
                or video.get('language') != 'English' or str(video.get('hidden', '0')) != '0'
                or not re.fullmatch(r'[A-Za-z0-9_-]{11}', external_id) or external_id in seen):
            continue
        selected.append(video)
        seen.add(external_id)
        if len(selected) == limit:
            break
    return selected


class Command(BaseCommand):
    help = 'Format verified BGG descriptions and import up to two associated English YouTube videos per inventory row.'

    def add_arguments(self, parser):
        parser.add_argument('--videos', action='store_true', help='Fetch public BGG video metadata.')
        parser.add_argument('--refresh', action='store_true')
        parser.add_argument('--cache-dir', type=Path, default=settings.BASE_DIR / '.catalog-import')

    def handle(self, *args, **options):
        cache = options['cache_dir']
        cache.mkdir(parents=True, exist_ok=True)
        session = requests.Session()
        session.headers['User-Agent'] = 'BG-Catalog/1.0 (personal inventory catalog)'
        formatted, imported, errors = 0, 0, 0
        for game in BoardGame.objects.filter(source_metadata__bgg_status='verified').order_by('id'):
            path = cache / f'bgg-{game.bgg_id}.json'
            if path.exists():
                item = json.loads(path.read_text(encoding='utf-8'))
                if str(item.get('objectid')) == game.bgg_id and item.get('description'):
                    game.description_html = sanitize_description(item['description'])
                    game.save(update_fields=['description_html'])
                    formatted += 1
            if not options['videos']:
                continue
            try:
                path = cache / f'videos-{game.bgg_id}.json'
                if path.exists() and not options['refresh']:
                    payload = json.loads(path.read_text(encoding='utf-8'))
                else:
                    time.sleep(0.5)
                    response = session.get('https://api.geekdo.com/api/videos', params={
                        'objecttype': 'thing', 'objectid': game.bgg_id, 'pageid': 1, 'showcount': 20, 'sort': 'hot',
                    }, timeout=25)
                    response.raise_for_status()
                    payload = response.json()
                    if not isinstance(payload.get('videos'), list):
                        raise ValueError('Unexpected BGG video response')
                    path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
                selected = select_videos(payload, game.bgg_id)
                with transaction.atomic():
                    GameVideo.objects.filter(game=game).update(is_active=False)
                    for video in selected:
                        source_url = f"https://boardgamegeek.com/video/{video['videoid']}"
                        GameVideo.objects.update_or_create(game=game, youtube_id=video['extvideoid'], defaults={
                            'title': video['title'][:255], 'category': video.get('gallery', ''),
                            'source_url': source_url, 'is_active': True,
                        })
                    metadata = dict(game.source_metadata)
                    metadata.update(video_status='imported' if selected else 'none_found',
                                    videos_checked_at=timezone.now().isoformat())
                    metadata.pop('video_error', None)
                    game.source_metadata = metadata
                    game.save(update_fields=['source_metadata'])
                imported += len(selected)
            except (requests.RequestException, ValueError, KeyError) as exc:
                metadata = dict(game.source_metadata)
                metadata.update(video_status='pending', video_error=str(exc))
                game.source_metadata = metadata
                game.save(update_fields=['source_metadata'])
                errors += 1
            self.stdout.write(f'{game.pk}: {game.name}: {game.source_metadata.get("video_status", "not requested")}')
        self.stdout.write(self.style.SUCCESS(f'Descriptions formatted: {formatted}; videos imported: {imported}; video errors: {errors}.'))
