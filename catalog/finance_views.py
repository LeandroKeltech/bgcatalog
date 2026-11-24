import csv
from decimal import Decimal

from django.contrib import messages
from .access import admin_group_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from .finance import ledger_summary, record_cash, record_sale, record_transfer
from .forms import CashForm, SaleForm, TransferForm
from .models import CashEntry, PartnerTransfer, Sale


@admin_group_required
def finance_dashboard(request):
    sales = Sale.objects.select_related('game').prefetch_related('entries')
    all_sales = list(sales)
    outstanding = sum((sale.outstanding for sale in all_sales), Decimal('0.00'))
    page = Paginator(all_sales, 24).get_page(request.GET.get('page'))
    return render(request, 'catalog/finance_dashboard.html', {
        'summary': ledger_summary(), 'outstanding': outstanding, 'sales': page.object_list,
        'page_obj': page, 'transfers': PartnerTransfer.objects.select_related('recorded_by')[:30],
        'recent_entries': CashEntry.objects.select_related('sale', 'recorded_by')[:30],
    })


@admin_group_required
def new_sale(request):
    initial = {'game': request.GET.get('game')}
    form = SaleForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        try:
            sale = record_sale(**form.cleaned_data, actor=request.user)
        except (ValueError, ValidationError) as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, 'Sale recorded. Add a payment when the money is received.')
            return redirect('sale_detail', sale_id=sale.pk)
    return render(request, 'catalog/ledger_form.html', {
        'form': form, 'title': 'Record a sale', 'submit_label': 'Record sale',
        'explanation': 'This records the sale and optionally deducts stock. It does not mark money as received.',
    })


@admin_group_required
def sale_detail(request, sale_id):
    sale = get_object_or_404(Sale.objects.prefetch_related('entries'), pk=sale_id)
    form = CashForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            record_cash(sale=sale, **form.cleaned_data, actor=request.user)
        except (ValueError, ValidationError) as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, 'Cash entry recorded and partner reconciliation updated.')
            return redirect('sale_detail', sale_id=sale.pk)
    bundle_sales = Sale.objects.none()
    if sale.reservation_id and sale.reservation.quote_group:
        bundle_sales = Sale.objects.filter(reservation__quote_group=sale.reservation.quote_group).select_related('reservation').prefetch_related('entries').order_by('pk')
    return render(request, 'catalog/sale_detail.html', {'sale': sale, 'form': form, 'bundle_sales': bundle_sales})


@admin_group_required
def partner_transfer(request):
    form = TransferForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            record_transfer(**form.cleaned_data, actor=request.user)
        except (ValueError, ValidationError) as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, 'Partner transfer recorded.')
            return redirect('finance_dashboard')
    return render(request, 'catalog/ledger_form.html', {
        'form': form, 'title': 'Record a partner transfer', 'submit_label': 'Record completed transfer',
        'explanation': 'Record money already transferred between you and your partner. This does not move money or create a new sale.',
        'summary': ledger_summary(),
    })


def csv_safe(value):
    value = str(value)
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) else value


@admin_group_required
def finance_export(request):
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="partner-reconciliation.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Type', 'Sale ID', 'Game', 'Customer', 'Handled by', 'Amount EUR', 'Reference', 'Recorded by', 'Recorded at'])
    for entry in CashEntry.objects.select_related('sale', 'recorded_by').order_by('date', 'id'):
        writer.writerow([entry.date, entry.get_kind_display(), entry.sale_id, csv_safe(entry.sale.game_name),
                         csv_safe(entry.sale.customer_name), entry.get_holder_display(), entry.signed_amount,
                         csv_safe(entry.reference), csv_safe(entry.recorded_by or ''), entry.created_at.isoformat()])
    for entry in PartnerTransfer.objects.select_related('recorded_by').order_by('date', 'id'):
        writer.writerow([entry.date, entry.get_direction_display(), '', '', '', 'Partner transfer', entry.signed_amount,
                         csv_safe(entry.reference), csv_safe(entry.recorded_by or ''), entry.created_at.isoformat()])
    writer.writerow([])
    writer.writerow(['All-time reconciliation (EUR)', 'Amount'])
    for key, value in ledger_summary().items():
        writer.writerow([key.replace('_', ' ').title(), value])
    return response
