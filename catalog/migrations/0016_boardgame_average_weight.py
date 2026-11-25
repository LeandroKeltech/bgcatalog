from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('catalog', '0015_buy_three_extra_discount')]

    operations = [
        migrations.AddField(
            model_name='boardgame',
            name='average_weight',
            field=models.FloatField(
                blank=True,
                help_text='BoardGameGeek community complexity rating (1 to 5)',
                null=True,
            ),
        ),
    ]
