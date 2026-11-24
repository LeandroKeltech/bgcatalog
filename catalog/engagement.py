"""Lightweight product popularity: no IP addresses or external analytics."""
from django.db.models import F
from django.utils import timezone

from .models import BoardGame

CLICK_WINDOW_SECONDS = 30 * 60


def count_product_click(request, game):
    """Count at most one open per product/session in a rolling 30-minute window."""
    if request.method != 'GET' or request.user.is_staff:
        return
    purpose = request.headers.get('Sec-Purpose', '') + request.headers.get('Purpose', '')
    if 'prefetch' in purpose.lower():
        return
    now = timezone.now().timestamp()
    recent = request.session.get('recent_product_clicks', {})
    key = str(game.pk)
    if now - recent.get(key, 0) < CLICK_WINDOW_SECONDS:
        return
    BoardGame.objects.filter(pk=game.pk).update(click_count=F('click_count') + 1)
    game.click_count += 1
    recent = {key: stamp for key, stamp in recent.items() if now - stamp < CLICK_WINDOW_SECONDS}
    recent[str(game.pk)] = now
    request.session['recent_product_clicks'] = recent
