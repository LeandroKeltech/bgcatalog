"""Durable admin alerts with optional email delivery after checkout commits."""
import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from .models import AdminReservationNotification
from .whatsapp import quote_message

logger = logging.getLogger(__name__)
NON_DELIVERING_BACKENDS = {
    'django.core.mail.backends.console.EmailBackend',
    'django.core.mail.backends.dummy.EmailBackend',
    'django.core.mail.backends.filebased.EmailBackend',
}


def delivery_backend_ready():
    if settings.EMAIL_BACKEND in NON_DELIVERING_BACKENDS:
        return False
    if settings.EMAIL_BACKEND == 'django.core.mail.backends.smtp.EmailBackend':
        return bool(settings.EMAIL_HOST and (not settings.EMAIL_HOST_USER or settings.EMAIL_HOST_PASSWORD))
    return True


def email_alerts_ready():
    try:
        validate_email(settings.RESERVATION_NOTIFICATION_EMAIL)
        validate_email(settings.DEFAULT_FROM_EMAIL)
    except ValidationError:
        return False
    return delivery_backend_ready()


def create_reservation_notification(quote):
    notification = AdminReservationNotification.objects.create(
        quote=quote, email_recipient=settings.RESERVATION_NOTIFICATION_EMAIL,
    )
    transaction.on_commit(lambda: send_reservation_alert(notification.pk), robust=True)
    return notification


def send_reservation_alert(notification_id):
    """Claim a single email attempt; failed/configuration-blocked attempts can be retried."""
    claimed = AdminReservationNotification.objects.filter(pk=notification_id).exclude(
        email_status__in=['sent', 'sending'],
    ).update(email_status='sending', email_attempted_at=timezone.now())
    if not claimed:
        return False
    notification = AdminReservationNotification.objects.select_related('quote').get(pk=notification_id)
    recipient = notification.email_recipient or settings.RESERVATION_NOTIFICATION_EMAIL
    try:
        validate_email(recipient)
        validate_email(settings.DEFAULT_FROM_EMAIL)
        configured = delivery_backend_ready()
    except ValidationError:
        configured = False
    if not configured:
        AdminReservationNotification.objects.filter(pk=notification_id).update(email_status='not_configured')
        return False
    body = ('A customer has reserved games on BG Catalog.\n'
            'This alert is independent of whether they send the WhatsApp message.\n'
            f'Current reservation status: {notification.quote.status}\n'
            'Reservation details at the time of checkout:\n\n' + quote_message(notification.quote) +
            '\n\nReview the quote reference in Admin Panel > Notifications. '
            'The reservation is not a confirmed sale or payment.\n')
    try:
        sent = send_mail(
            subject=f'New reservation — BG Catalog — {notification.quote_id}', message=body,
            from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[recipient], fail_silently=False,
        )
        if sent != 1:
            raise RuntimeError('Email backend did not accept the message')
    except Exception:
        logger.warning('Reservation alert email failed for notification %s', notification_id)
        AdminReservationNotification.objects.filter(pk=notification_id).update(email_status='failed')
        return False
    AdminReservationNotification.objects.filter(pk=notification_id).update(
        email_status='sent', email_recipient=recipient, email_sent_at=timezone.now(),
    )
    return True
