from django.conf import settings
from django.db import migrations


def rename_group(apps, schema_editor):
    alias = schema_editor.connection.alias
    Group = apps.get_model('auth', 'Group')
    User = apps.get_model(settings.AUTH_USER_MODEL)
    old = Group.objects.using(alias).filter(name='usuario_comum').first()
    if old is None:
        Group.objects.using(alias).get_or_create(name='user')
        return
    target = Group.objects.using(alias).filter(name='user').first()
    if target is None:
        old.name = 'user'
        old.save(using=alias, update_fields=['name'])
        return
    # Preserve memberships and permissions if both names already exist.
    for user in User.objects.using(alias).filter(groups=old).iterator():
        user.groups.add(target)
    target.permissions.add(*old.permissions.values_list('pk', flat=True))
    old.delete(using=alias)


class Migration(migrations.Migration):
    dependencies = [('catalog', '0008_account_roles')]
    operations = [migrations.RunPython(rename_group, migrations.RunPython.noop)]
