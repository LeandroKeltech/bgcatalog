from django.conf import settings
from django.db import migrations


def assign_existing_roles(apps, schema_editor):
    alias = schema_editor.connection.alias
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    admin, _ = Group.objects.using(alias).get_or_create(name='admin')
    common, _ = Group.objects.using(alias).get_or_create(name='usuario_comum')
    for user in User.objects.using(alias).all().iterator():
        if user.is_superuser or user.groups.filter(pk=admin.pk).exists():
            user.groups.add(admin)
            user.groups.remove(common)
        else:
            user.groups.add(common)


class Migration(migrations.Migration):
    dependencies = [
        ('catalog', '0007_boardgame_click_count_boardgame_game_relevance_idx'),
        ('auth', '0012_alter_user_first_name_max_length'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [migrations.RunPython(assign_existing_roles, migrations.RunPython.noop)]
