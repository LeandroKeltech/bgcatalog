"""Import the read-only Sheets snapshot and optionally validate against BGG."""

import csv
import json
import re
import time
import unicodedata
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from catalog.models import BoardGame


def money(value):
    if value in ('', None):
        return None
    try:
        result = Decimal(str(value).replace('€', '').strip())
        if not result.is_finite() or result < 0:
            return None
        return result.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except InvalidOperation:
        return None


def normalized(value):
    value = unicodedata.normalize('NFKD', value).casefold()
    return re.sub(r'[^a-z0-9]', '', value)


def bgg_id_from_url(value):
    url = urlparse(value)
    if url.hostname not in ('boardgamegeek.com', 'www.boardgamegeek.com'):
        return None
    match = re.match(r'^/(?:boardgame|boardgameexpansion|rpgitem)/(\d+)(?:/|$)', url.path)
    return match.group(1) if match else None


class Command(BaseCommand):
    help = 'Import inventory from a Sheets snapshot; optionally enrich from BGG public website data.'

    def add_arguments(self, parser):
        parser.add_argument('--source', type=Path, default=settings.BASE_DIR / 'catalog/data/source_catalog.json')
        parser.add_argument('--enrich', action='store_true')
        parser.add_argument('--refresh', action='store_true', help='Refresh cached BGG responses.')
        parser.add_argument('--cache-dir', type=Path, default=settings.BASE_DIR / '.catalog-import')
        parser.add_argument('--mappings', type=Path, help='Reviewed source ID to BGG ID mappings.')

    def handle(self, *args, **options):
        try:
            source = json.loads(options['source'].read_text(encoding='utf-8'))
            headers, *rows = source['values']
            mapping_path = options['mappings'] or settings.BASE_DIR / 'catalog/data/bgg_mappings.json'
            mapping_doc = json.loads(mapping_path.read_text(encoding='utf-8')) if mapping_path.exists() else {}
            mappings = mapping_doc.get('mappings', {}) if mapping_doc.get('spreadsheet_id') == source['spreadsheet_id'] else {}
        except (OSError, ValueError, KeyError) as exc:
            raise CommandError(f'Cannot read the source or mappings: {exc}') from exc
        required = {'Name', 'BGG Link', 'Price', 'id', 'MSRP (€)', 'State', 'balance', 'status'}
        if not required.issubset(headers):
            raise CommandError('The snapshot is missing required inventory columns.')
        records = [dict(zip(headers, row)) for row in rows if row and row[0]]
        ids = [str(row.get('id', '')) for row in records]
        if '' in ids or len(ids) != len(set(ids)):
            raise CommandError('Source inventory IDs must be present and unique.')
        # Validate the entire inventory before writing any row.
        prepared = []
        for row in records:
            try:
                quantity = Decimal(str(row['balance']))
                if not quantity.is_finite() or quantity < 0 or quantity != int(quantity):
                    raise ValueError
                condition = row['State'].strip().lower().replace(' ', '_')
                if condition not in dict(BoardGame.CONDITION_CHOICES):
                    raise ValueError
                if row['status'].strip().upper() == 'SOLD OUT' and quantity != 0:
                    raise ValueError
            except (ValueError, InvalidOperation):
                raise CommandError(f"Invalid stock, status, or condition for source ID {row['id']}")
            prepared.append((row, int(quantity), condition))
        report = []
        cache_dir = options['cache_dir']
        cache_dir.mkdir(parents=True, exist_ok=True)
        session = requests.Session()
        session.headers['User-Agent'] = 'BG-Catalog/1.0 (personal inventory import)'
        created_count = 0
        for row, quantity, condition in prepared:
            source_id = str(row['id'])
            key = f"{source['spreadsheet_id']}:{source_id}"
            with transaction.atomic():
                game, created = BoardGame.objects.get_or_create(source_key=key, defaults={
                    'name': row['Name'], 'description': row.get('Description', ''),
                    'msrp_price': money(row.get('MSRP (€)')), 'sale_price': money(row.get('Price')),
                    'condition': condition, 'stock_quantity': quantity, 'is_sold': quantity == 0,
                    'notes': row.get('Notes', ''),
                    'source_metadata': {'spreadsheet_id': source['spreadsheet_id'],
                                        'sheet_name': source['sheet_name'], 'row': row,
                                        'bgg_status': 'pending'},
                })
            created_count += created
            metadata = dict(game.source_metadata)
            mapping = mappings.get(source_id, {})
            candidate = str(mapping.get('bgg_id') or bgg_id_from_url(row.get('BGG Link', '')) or '')
            issue = ''
            if money(row.get('Price')) is None:
                issue = 'Missing or invalid spreadsheet sale price'
            already_verified = (metadata.get('bgg_status') == 'verified' and game.bgg_id == candidate)
            if options['enrich'] and (not already_verified or options['refresh']):
                try:
                    if not candidate.isdigit():
                        raise ValueError('No BGG identity supplied; needs a reviewed mapping')
                    item = self.fetch_item(session, candidate, cache_dir, options['refresh'])
                    names = [item.get('name', '')] + [n['name'] for n in item.get('alternatenames', [])]
                    if mapping and normalized(mapping['expected_name']) != normalized(item.get('name', '')):
                        raise ValueError('The reviewed mapping does not match the current BGG name')
                    if source_id not in mappings and normalized(game.name) not in {normalized(n) for n in names}:
                        raise ValueError(f"Identity needs review: BGG {candidate} is {item.get('name')!r}")
                    description = BeautifulSoup(item.get('description', ''), 'html.parser').get_text(' ', strip=True)
                    if not description:
                        raise ValueError('BGG description is missing')
                    artwork = item
                    if mapping.get('version_id'):
                        artwork = self.fetch_item(session, str(mapping['version_id']), cache_dir,
                                                  options['refresh'], objecttype='version')
                        if normalized(artwork.get('name', '')) != normalized(mapping['version_name']):
                            raise ValueError('BGG edition name does not match the reviewed mapping')
                        parents = artwork.get('links', {}).get('boardgame', [])
                        if candidate not in {str(p['objectid']) for p in parents}:
                            raise ValueError('BGG edition does not belong to the mapped game')
                    images = artwork.get('images', {})
                    image = images.get('original') or artwork.get('imageurl', '')
                    thumbnail = images.get('thumb') or image
                    self.validate_image(session, image)
                    self.validate_image(session, thumbnail)
                    game.bgg_id = candidate
                    game.description = description
                    from catalog.content import sanitize_description
                    game.description_html = sanitize_description(item.get('description', ''))
                    game.image_url, game.thumbnail_url = image, thumbnail
                    for target, field in (
                        ('year_published', 'yearpublished'), ('min_players', 'minplayers'),
                        ('max_players', 'maxplayers'), ('min_playtime', 'minplaytime'),
                        ('max_playtime', 'maxplaytime'), ('min_age', 'minage'),
                    ):
                        value = item.get(field)
                        setattr(game, target, int(value) if value not in (None, '') else None)
                    weight = item.get('stats', {}).get('averageweight')
                    try:
                        weight = float(weight) if weight not in (None, '', 'N/A') else None
                    except (TypeError, ValueError):
                        weight = None
                    game.average_weight = weight if weight is not None and 0 < weight <= 5 else None
                    for target, field in (('designer', 'boardgamedesigner'),
                                          ('categories', 'boardgamecategory'), ('mechanics', 'boardgamemechanic')):
                        limit = BoardGame._meta.get_field(target).max_length
                        setattr(game, target, ', '.join(n['name'] for n in item.get('links', {}).get(field, []))[:limit])
                    metadata.update(bgg_status='verified', bgg_verified_at=timezone.now().isoformat(),
                                    bgg_name=item['name'], bgg_url=item.get('canonical_link', ''),
                                    identity_basis='reviewed mapping' if source_id in mappings else 'exact name or alias',
                                    identity_note=mapping.get('reason', ''),
                                    bgg_version_id=mapping.get('version_id'),
                                    description_source='RPGGeek' if item.get('subtype') == 'rpgitem' else 'BoardGameGeek',
                                    image_source='RPGGeek' if item.get('subtype') == 'rpgitem' else 'BoardGameGeek')
                    metadata.pop('bgg_error', None)
                except (requests.RequestException, ValueError, KeyError) as exc:
                    metadata.update(bgg_status='pending', bgg_error=str(exc))
                metadata['bgg_candidate_id'] = candidate
                game.source_metadata = metadata
                game.full_clean()
                game.save()
            report.append({'source_id': source_id, 'name': game.name, 'bgg_id': game.bgg_id or '',
                           'status': metadata.get('bgg_status', 'pending'),
                           'issue': '; '.join(x for x in (issue, metadata.get('bgg_error', '')) if x)})
            self.stdout.write(f"{source_id}: {game.name}: {metadata.get('bgg_status', 'pending')}")
        with (cache_dir / 'import-report.csv').open('w', newline='', encoding='utf-8') as stream:
            writer = csv.DictWriter(stream, fieldnames=['source_id', 'name', 'bgg_id', 'status', 'issue'])
            writer.writeheader()
            writer.writerows(report)
        verified = sum(r['status'] == 'verified' for r in report)
        self.stdout.write(self.style.SUCCESS(
            f'Imported {len(records)} source rows: {created_count} created, '
            f'{len(records) - created_count} existing. BGG verified: {verified}; pending: {len(records) - verified}. '
            f'Report: {cache_dir / "import-report.csv"}'
        ))

    def fetch_item(self, session, candidate, cache_dir, refresh, objecttype='thing'):
        cache_key = candidate if objecttype == 'thing' else f'{objecttype}-{candidate}'
        path = cache_dir / f'bgg-{cache_key}.json'
        if path.exists() and not refresh:
            item = json.loads(path.read_text(encoding='utf-8'))
        else:
            time.sleep(0.5)
            response = session.get('https://api.geekdo.com/api/geekitems',
                                   params={'objecttype': objecttype, 'objectid': candidate}, timeout=30)
            response.raise_for_status()
            item = response.json()['item']
            path.write_text(json.dumps(item, ensure_ascii=False), encoding='utf-8')
        if str(item.get('objectid')) != candidate:
            raise ValueError('BGG response does not match the requested identity')
        return item

    def validate_image(self, session, url):
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.hostname != 'cf.geekdo-images.com':
            raise ValueError('BGG returned an unexpected image host or URL')
        response = session.head(url, timeout=20, allow_redirects=False)
        response.raise_for_status()
        if response.status_code != 200 or not response.headers.get('Content-Type', '').startswith('image/'):
            raise ValueError('BGG image is not an accessible image')
