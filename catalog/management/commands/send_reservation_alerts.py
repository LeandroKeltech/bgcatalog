from django.core.management.base import BaseCommand

from catalog.models import AdminReservationNotification
from catalog.notifications import send_reservation_alert


class Command(BaseCommand):
    help = 'Retry up to 100 pending, failed or unconfigured reservation emails. Already sent emails are skipped.'

    def handle(self, *args, **options):
        ids = list(AdminReservationNotification.objects.filter(
            email_status__in=['pending', 'failed', 'not_configured'],
        ).order_by('pk').values_list('pk', flat=True)[:100])
        sent = sum(send_reservation_alert(pk) for pk in ids)
        self.stdout.write(f'Email attempts: {len(ids)}; accepted by email service: {sent}.')
