"""Assign accounts to one of the two roles, including after role changes."""
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from .access import ADMIN_GROUP, USER_GROUP

User = get_user_model()


def sync_role(user, using):
    common, _ = Group.objects.using(using).get_or_create(name=USER_GROUP)
    if user.groups.filter(name=ADMIN_GROUP).exists():
        if user.groups.filter(pk=common.pk).exists():
            user.groups.remove(common)
    elif not user.groups.filter(pk=common.pk).exists():
        user.groups.add(common)


@receiver(post_save, sender=User)
def assign_role(sender, instance, created, raw, using, **kwargs):
    if raw:
        return
    # Explicit createsuperuser is the bootstrap path; flags on existing accounts
    # never bypass the group check or restore a revoked administrator role.
    if created and instance.is_superuser:
        group, _ = Group.objects.using(using).get_or_create(name=ADMIN_GROUP)
        instance.groups.add(group)
    sync_role(instance, using)


@receiver(m2m_changed, sender=User.groups.through)
def maintain_role(sender, instance, action, reverse, using, pk_set, **kwargs):
    if action == 'pre_clear' and reverse:
        instance._role_user_ids = list(instance.user_set.values_list('pk', flat=True))
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return
    if reverse:
        ids = getattr(instance, '_role_user_ids', []) if action == 'post_clear' else pk_set
        for user in User.objects.using(using).filter(pk__in=ids):
            sync_role(user, using)
    else:
        sync_role(instance, using)
