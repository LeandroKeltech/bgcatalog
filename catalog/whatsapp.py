"""Build click-to-chat links. This module never sends a message."""
import re
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone


def shop_whatsapp_number():
    number = re.sub(r'[\s+().-]', '', settings.WHATSAPP_SHOP_NUMBER)
    if not re.fullmatch(r'[1-9][0-9]{7,14}', number):
        raise ImproperlyConfigured('A valid WHATSAPP_SHOP_NUMBER is required for checkout.')
    return number


def whatsapp_url(message):
    return f'https://wa.me/{shop_whatsapp_number()}?{urlencode({"text": message})}'


def quote_message(quote):
    data = quote.snapshot
    contact = data['contact']
    lines = [f'Hello! I would like to order these games.', f'Quote: {quote.pk}',
             f'Name: {contact["full_name"]}', f'Email: {contact["email"]}',
             f'Phone: {contact["phone"]}', '']
    for line in data['lines']:
        lines.append(f'{line["quantity"]} × {line["name"]} ({line["condition"]}) — €{line["line_total"]}')
        for group in line['price_groups']:
            lines.append(f'  {group["quantity"]} × €{group["unit_price"]}')
    lines += ['', f'Subtotal before offers: €{data["subtotal"]}', f'Discount: €{data["discount"]}',
              f'Total: €{data["total"]}', 'Delivery/collection and any shipping charge to be agreed.']
    if data.get('offer'):
        lines.append(f'Offer: {data["offer"]}')
    if data.get('offer_rule'):
        lines += [data['offer_rule'], 'Promotion bundle items must be confirmed together.']
    lines += [f'Reservation expires: {timezone.localtime(quote.reservation_expires_at):%d %b %Y %H:%M} (Dublin time).',
              'Please confirm availability and payment arrangements.']
    return '\n'.join(lines)
