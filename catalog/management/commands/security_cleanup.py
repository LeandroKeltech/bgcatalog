from django.core.management import BaseCommand, call_command
from django.utils import timezone

from catalog.models import SecurityRateLimit, StockReservation


class Command(BaseCommand):
    help = 'Remove expired rate-limit counters and sessions, and expire old reservations.'

    def handle(self, *args, **options):
        count, _ = SecurityRateLimit.objects.filter(expires_at__lte=timezone.now()).delete()
        StockReservation.expire_old_reservations()
        call_command('clearsessions', verbosity=0)
        self.stdout.write(f'Removed {count} expired counters; reservations and sessions cleaned.')
