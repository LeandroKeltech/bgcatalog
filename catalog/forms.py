import uuid
from decimal import Decimal

from django import forms
from django.utils import timezone

from .models import BoardGame, CashEntry, PartnerTransfer, Promotion


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if isinstance(field.widget, forms.HiddenInput):
                continue
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs['class'] = 'game-choices'
                continue
            field.widget.attrs['class'] = (
                'form-check-input' if isinstance(field.widget, forms.CheckboxInput)
                else 'form-select' if isinstance(field.widget, forms.Select) else 'form-control'
            )
            if isinstance(field.widget, forms.Textarea):
                field.widget.attrs['rows'] = 3
            if isinstance(field, forms.DecimalField):
                field.widget.attrs['inputmode'] = 'decimal'


class InventoryForm(StyledFormMixin, forms.ModelForm):
    class Meta:
        model = BoardGame
        fields = ['name', 'stock_quantity', 'condition', 'average_weight', 'msrp_price', 'sale_price', 'notes']
        labels = {'msrp_price': 'Original price / MSRP (€)', 'sale_price': 'Our selling price (€)',
                  'stock_quantity': 'Current stock', 'average_weight': 'Difficulty / complexity (BGG 1–5)'}

    def clean_stock_quantity(self):
        quantity = self.cleaned_data['stock_quantity']
        reserved = self.instance.reserved_quantity if self.instance.pk else 0
        if quantity < reserved:
            raise forms.ValidationError(f'At least {reserved} units are currently reserved.')
        return quantity

    def save(self, commit=True):
        self.instance.is_sold = self.cleaned_data['stock_quantity'] == 0
        return super().save(commit=commit)


class LedgerForm(StyledFormMixin, forms.Form):
    request_id = forms.UUIDField(widget=forms.HiddenInput, initial=uuid.uuid4)

    def clean_date(self):
        value = self.cleaned_data['date']
        if value > timezone.localdate():
            raise forms.ValidationError('Record actual transactions using today or an earlier date.')
        return value


class SaleForm(LedgerForm):
    game = forms.ModelChoiceField(queryset=BoardGame.objects.order_by('name', 'id'))
    quantity = forms.IntegerField(min_value=1, max_value=10000, initial=1)
    unit_price = forms.DecimalField(min_value=0, max_digits=10, decimal_places=2, required=False,
                                    label='Selling price per copy (€)', help_text='Leave blank to use the current catalog price.')
    customer_name = forms.CharField(max_length=255, required=False, label='Customer / buyer')
    reference = forms.CharField(max_length=100, required=False, label='Sale reference')
    sale_date = forms.DateField(initial=timezone.localdate, widget=forms.DateInput(attrs={'type': 'date'}))
    deduct_stock = forms.BooleanField(initial=True, required=False, label='Deduct from current stock',
                                     help_text='Clear only for a historical sale whose stock was already adjusted.')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['game'].label_from_instance = lambda game: (
            f'{game.name} — Stock: {game.stock_quantity} — {game.get_condition_display()} (#{game.pk})'
        )

    def clean_sale_date(self):
        value = self.cleaned_data['sale_date']
        if value > timezone.localdate():
            raise forms.ValidationError('A sale date cannot be in the future.')
        return value

    def clean(self):
        cleaned = super().clean()
        game = cleaned.get('game')
        if game and cleaned.get('unit_price') is None:
            cleaned['unit_price'] = game.final_price
            if game.final_price is None:
                self.add_error('unit_price', 'Enter a selling price for this game.')
        return cleaned


class CashForm(LedgerForm):
    kind = forms.ChoiceField(choices=CashEntry.KIND_CHOICES)
    amount = forms.DecimalField(min_value=Decimal('0.01'), max_digits=12, decimal_places=2, label='Amount (€)')
    holder = forms.ChoiceField(choices=CashEntry.HOLDER_CHOICES, label='Money received / refunded by')
    method = forms.ChoiceField(choices=CashEntry.METHOD_CHOICES)
    date = forms.DateField(initial=timezone.localdate, widget=forms.DateInput(attrs={'type': 'date'}))
    reference = forms.CharField(max_length=150, required=False, label='Payment reference')
    notes = forms.CharField(widget=forms.Textarea, required=False)


class TransferForm(LedgerForm):
    direction = forms.ChoiceField(choices=PartnerTransfer.DIRECTION_CHOICES)
    amount = forms.DecimalField(min_value=Decimal('0.01'), max_digits=12, decimal_places=2, label='Amount (€)')
    date = forms.DateField(initial=timezone.localdate, widget=forms.DateInput(attrs={'type': 'date'}))
    reference = forms.CharField(max_length=150, label='Transfer reference / receipt')
    notes = forms.CharField(widget=forms.Textarea, required=False)


class PromotionForm(StyledFormMixin, forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['games'].queryset = BoardGame.objects.order_by('name', 'id')
        self.fields['value'].required = False
        self.fields['minimum_quantity'].required = False
        self.fields['minimum_quantity'].min_value = 2
        self.fields['minimum_quantity'].max_value = 100
        self.fields['minimum_quantity'].widget.attrs.update(min=2, max=100)
        self.fields['games'].label_from_instance = lambda game: (
            f'{game.name} — {game.get_condition_display()} (#{game.pk})'
        )

    class Meta:
        model = Promotion
        fields = ['name', 'kind', 'value', 'minimum_quantity', 'repeat_free_groups', 'is_active', 'apply_to_all', 'games', 'starts_at', 'ends_at', 'description']
        labels = {'kind': 'Promotion type', 'value': 'Discount / promotional price',
                  'is_active': 'Enabled', 'apply_to_all': 'Apply to the whole catalog',
                  'minimum_quantity': 'Minimum eligible copies in cart',
                  'repeat_free_groups': 'Repeat cheapest-free offer for every complete group'}
        widgets = {
            'starts_at': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
            'ends_at': forms.DateTimeInput(format='%Y-%m-%dT%H:%M', attrs={'type': 'datetime-local'}),
            'games': forms.CheckboxSelectMultiple(),
        }
        help_texts = {'starts_at': 'Dublin local time.', 'ends_at': 'Dublin local time. Leave blank for no end date.',
                      'value': 'Percentage or euro amount, depending on the type. Leave blank for cheapest-free offers.',
                      'minimum_quantity': 'Cart offers only. Buy 5 / cheapest free means 5 copies total: pay for 4. Multiple copies of a title count. Ignored for individual-game discounts.',
                      'repeat_free_groups': 'Cheapest-free offers only. With a group size of 5, 10 copies give 2 free. Highest-value copies are grouped first for the best saving. Otherwise only one cheapest copy is free per cart.',
                      'games': 'Choose games, or enable the whole catalog. Only the best offer applies; discounts do not stack.'}

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get('kind')
        if kind == 'cheapest_free':
            cleaned['value'] = Decimal('0')
        elif cleaned.get('value') is None:
            self.add_error('value', 'Enter the discount or promotional price.')
        if not cleaned.get('minimum_quantity'):
            if kind in Promotion.CART_KINDS:
                self.add_error('minimum_quantity', 'Enter a minimum of 2 to 100 eligible copies.')
            else:
                cleaned['minimum_quantity'] = 2
        if not cleaned.get('apply_to_all') and not cleaned.get('games'):
            self.add_error('games', 'Choose at least one game or apply the promotion to the whole catalog.')
        return cleaned
