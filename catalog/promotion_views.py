from django.contrib import messages
from .access import admin_group_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import PromotionForm
from .models import Promotion


@admin_group_required
def promotion_list(request):
    page = Paginator(Promotion.objects.prefetch_related('games'), 24).get_page(request.GET.get('page'))
    return render(request, 'catalog/promotion_list.html', {'page_obj': page, 'promotions': page.object_list})


@admin_group_required
def promotion_edit(request, promotion_id=None):
    promotion = get_object_or_404(Promotion, pk=promotion_id) if promotion_id else None
    form = PromotionForm(request.POST or None, instance=promotion)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Promotion saved. The best active offer is applied automatically.')
        return redirect('promotion_list')
    return render(request, 'catalog/ledger_form.html', {
        'form': form, 'title': 'Edit promotion' if promotion else 'Create promotion',
        'submit_label': 'Save promotion', 'cancel_url': 'promotion_list',
        'promotion_form': True,
        'explanation': 'Create individual-game discounts or quantity-based cart offers. The best total wins, without stacking. Cart mechanics count copies of eligible games, including repeated copies of the same title.',
    })


@admin_group_required
@require_POST
def promotion_toggle(request, promotion_id):
    promotion = get_object_or_404(Promotion, pk=promotion_id)
    promotion.is_active = not promotion.is_active
    promotion.save(update_fields=['is_active'])
    messages.success(request, 'Promotion enabled.' if promotion.is_active else 'Promotion paused.')
    return redirect('promotion_list')
