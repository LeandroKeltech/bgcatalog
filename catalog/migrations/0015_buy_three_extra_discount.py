from datetime import datetime, timezone
from decimal import Decimal

from django.db import migrations


def create_offer(apps, schema_editor):
    Promotion = apps.get_model('catalog', 'Promotion')
    Promotion.objects.using(schema_editor.connection.alias).create(
        name='Buy 3+, get an extra 10% off', kind='cart_extra_percent',
        value=Decimal('10.00'), minimum_quantity=3, apply_to_all=True,
        is_active=True, starts_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        description='Buy 3 or more games and get an extra 10% off final game prices, '
                    'including existing game discounts. Counts physical copies. '
                    'Applied once to the eligible subtotal; other cart offers do not stack.',
    )


def remove_offer(apps, schema_editor):
    apps.get_model('catalog', 'Promotion').objects.using(schema_editor.connection.alias).filter(
        kind='cart_extra_percent', name='Buy 3+, get an extra 10% off',
    ).delete()


class Migration(migrations.Migration):
    dependencies = [('catalog', '0014_remove_promotion_promotion_kind_valid_and_more')]
    operations = [migrations.RunPython(create_offer, remove_offer)]
