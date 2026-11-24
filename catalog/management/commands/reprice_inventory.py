"""Apply the user-approved condition pricing policy with a local recovery snapshot."""
import json
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from catalog.condition_pricing import CONDITION_DISCOUNTS, condition_price
from catalog.models import BoardGame


class Command(BaseCommand):
    help = 'Preview condition pricing: New 30%, Like New 40%, Used 60% off original prices. Use --apply to save.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')
        parser.add_argument('--backup-dir', type=Path, default=settings.BASE_DIR / '.catalog-import')

    @transaction.atomic
    def handle(self, *args, **options):
        games = BoardGame.objects.order_by('pk')
        if options['apply']:
            games = games.select_for_update()
        changes, skipped = [], []
        for game in games:
            price = condition_price(game.msrp_price, game.condition)
            if price is None:
                skipped.append(game.name)
                continue
            discount = CONDITION_DISCOUNTS[game.condition]
            if game.sale_price != price or game.discount_percentage != discount:
                changes.append((game, price, discount))

        if options['apply'] and changes:
            stamp = timezone.now()
            backup = options['backup_dir'] / f'condition-pricing-{stamp:%Y%m%dT%H%M%S}-{uuid4().hex[:8]}.json'
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_text(json.dumps({
                'created_at': stamp.isoformat(), 'policy': CONDITION_DISCOUNTS,
                'games': [{'id': game.pk, 'name': game.name, 'condition': game.condition,
                           'original_price': str(game.msrp_price),
                           'sale_price': str(game.sale_price) if game.sale_price is not None else None,
                           'discount_percentage': game.discount_percentage,
                           'previous_pricing_override': game.source_metadata.get('pricing_override')}
                          for game, price, discount in changes],
            }, indent=2, ensure_ascii=False), encoding='utf-8')
            self.stdout.write(f'Recovery snapshot: {backup}')
            for game, price, discount in changes:
                metadata = dict(game.source_metadata)
                metadata['pricing_override'] = {
                    'reason': 'Condition pricing policy requested by the user',
                    'condition': game.condition, 'discount_percentage': discount,
                    'original_price': str(game.msrp_price), 'sale_price': str(price),
                    'updated_at': stamp.isoformat(),
                }
                game.sale_price, game.discount_percentage, game.source_metadata = price, discount, metadata
                game.save(update_fields=['sale_price', 'discount_percentage', 'source_metadata', 'updated_at'])
        self.stdout.write(f"{'Updated' if options['apply'] else 'Would update'} {len(changes)} entries. Skipped {len(skipped)} without an original price.")
        for name in skipped:
            self.stdout.write(f'Unchanged price: {name}')
