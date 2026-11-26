from decimal import Decimal

from django.db import migrations


def increase_discount(apps, schema_editor):
    apps.get_model('catalog', 'Promotion').objects.using(schema_editor.connection.alias).filter(
        name='Buy 3+, get an extra 10% off', kind='cart_extra_percent',
        minimum_quantity=3, apply_to_all=True, value=Decimal('10.00'),
    ).update(
        name='Buy 3+, get an extra 20% off', value=Decimal('20.00'),
        description='Buy 3 or more games and get an extra 20% off final game prices, '
                    'including existing game discounts. Counts physical copies. '
                    'Applied once to the eligible subtotal; other cart offers do not stack.',
    )


def restore_discount(apps, schema_editor):
    apps.get_model('catalog', 'Promotion').objects.using(schema_editor.connection.alias).filter(
        name='Buy 3+, get an extra 20% off', kind='cart_extra_percent',
        minimum_quantity=3, apply_to_all=True, value=Decimal('20.00'),
    ).update(
        name='Buy 3+, get an extra 10% off', value=Decimal('10.00'),
        description='Buy 3 or more games and get an extra 10% off final game prices, '
                    'including existing game discounts. Counts physical copies. '
                    'Applied once to the eligible subtotal; other cart offers do not stack.',
    )


class Migration(migrations.Migration):
    dependencies = [('catalog', '0017_alter_customerquote_user')]
    operations = [migrations.RunPython(increase_discount, restore_discount)]
