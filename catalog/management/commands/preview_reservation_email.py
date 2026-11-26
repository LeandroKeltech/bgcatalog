"""Render example emails using fictional data, without sending or accessing the DB."""
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace

from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.utils import timezone


class Command(BaseCommand):
    help = 'Write fictional customer and shop email HTML previews; no email is sent.'

    def add_arguments(self, parser):
        parser.add_argument('--output-dir', default='outputs/email-previews')

    def handle(self, *args, **options):
        quote = SimpleNamespace(
            pk='EXAMPLE-RESERVATION', status='Active',
            reservation_expires_at=timezone.now() + timedelta(hours=24),
            snapshot={
                'contact': {'full_name': 'Alex', 'email': 'alex@example.com', 'phone': ''},
                'lines': [
                    {'name': 'Catan', 'condition': 'Like new', 'quantity': 1,
                     'line_total': '30.00', 'price_groups': [{'quantity': 1, 'unit_price': '30.00'}]},
                    {'name': 'Ticket to Ride', 'condition': 'Good', 'quantity': 1,
                     'line_total': '25.00', 'price_groups': [{'quantity': 1, 'unit_price': '25.00'}]},
                ],
                'subtotal': '60.00', 'discount': '5.00', 'total': '55.00',
                'offer': 'Example offer', 'offer_rule': '',
            },
        )
        directory = Path(options['output_dir'])
        directory.mkdir(parents=True, exist_ok=True)
        for audience in ('guest', 'customer', 'shop'):
            html = render_to_string('catalog/emails/reservation.html', {
                'quote': quote, 'is_guest': audience == 'guest', 'is_admin': audience == 'shop',
                'reservation_url': 'https://example.com/reservation-preview',
            })
            path = directory / f'{audience}-reservation.html'
            path.write_text(html, encoding='utf-8')
            self.stdout.write(str(path.resolve()))
