"""Group membership is the authority for every administrative entry point."""
from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.urls import reverse

ADMIN_GROUP = 'admin'
USER_GROUP = 'user'


def is_admin(user):
    return bool(user.is_authenticated and user.is_active
                and user.groups.filter(name=ADMIN_GROUP).exists())


def admin_group_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path(), reverse('admin:login'))
        if not is_admin(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


def admin_access(request):
    allowed = is_admin(request.user)
    context = {'can_access_admin': allowed}
    if allowed:
        from .models import AdminReservationNotification
        context['reservation_unread_count'] = AdminReservationNotification.objects.exclude(read_by=request.user).count()
        context['reservation_notification_cursor'] = AdminReservationNotification.objects.values_list('pk', flat=True).first() or 0
    return context
