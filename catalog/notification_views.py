from urllib.parse import urlencode

from django.core.paginator import Paginator
from django.db.models import Exists, OuterRef
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from .access import admin_group_required
from .models import AdminReservationNotification
from .notifications import email_alerts_ready, send_reservation_alert
from django.contrib import messages


@admin_group_required
@require_GET
def notification_list(request):
    receipts = AdminReservationNotification.read_by.through.objects.filter(
        adminreservationnotification_id=OuterRef('pk'), user_id=request.user.pk,
    )
    notifications = AdminReservationNotification.objects.select_related('quote').annotate(is_read=Exists(receipts))
    page = Paginator(notifications, 30).get_page(request.GET.get('page'))
    return render(request, 'catalog/notifications.html', {
        'notifications': page, 'notification_email_ready': email_alerts_ready(),
    })


@admin_group_required
@require_GET
def notification_status(request):
    try:
        after = int(request.GET.get('after', '0'))
        if not 0 <= after <= 9223372036854775807:
            raise ValueError
    except (ValueError, TypeError):
        return JsonResponse({'error': 'Invalid notification cursor.'}, status=400)
    # Use a stable upper bound so concurrent arrivals appear on the following poll.
    latest = AdminReservationNotification.objects.values_list('pk', flat=True).first() or 0
    unread = AdminReservationNotification.objects.filter(pk__lte=latest).exclude(read_by=request.user)
    return JsonResponse({'unread_count': unread.count(), 'latest_id': latest,
                         'new_count': unread.filter(pk__gt=after).count()})


@admin_group_required
@require_POST
def notification_open(request, notification_id):
    notification = get_object_or_404(AdminReservationNotification, pk=notification_id)
    notification.read_by.add(request.user)
    return redirect(reverse('reservation_management') + '?' + urlencode({'quote': notification.quote_id, 'status': ''}))


@admin_group_required
@require_POST
def notification_retry_email(request, notification_id):
    notification = get_object_or_404(AdminReservationNotification, pk=notification_id)
    if send_reservation_alert(notification.pk):
        messages.success(request, 'Reservation alert accepted by the email service.')
    else:
        notification.refresh_from_db()
        messages.info(request, f'Email status: {notification.get_email_status_display()}.')
    return redirect('notification_list')
