"""Country-aware phone input; profiles continue to store one E.164 string."""
import re

import phonenumbers
from django import forms

from .phone_countries import PHONE_COUNTRIES


COUNTRY_DETAILS = {region: (name, code) for region, name, code in PHONE_COUNTRIES}
COUNTRY_CHOICES = [(region, f'{name} (+{code})') for region, name, code in PHONE_COUNTRIES]


class PhoneCountrySelect(forms.Select):
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        country, code = COUNTRY_DETAILS[value]
        option['attrs'].update({'data-country': country, 'data-dial-code': f'+{code}'})
        return option


class InternationalPhoneWidget(forms.MultiWidget):
    template_name = 'catalog/widgets/international_phone.html'

    class Media:
        css = {'all': ('catalog/css/phone-country.css?v=20261125',)}
        js = ('catalog/js/phone-country.js?v=20261125',)

    def __init__(self, attrs=None):
        super().__init__((
            PhoneCountrySelect(choices=COUNTRY_CHOICES, attrs={
                'class': 'form-select phone-country-native', 'autocomplete': 'off',
            }),
            forms.TextInput(attrs={
                'type': 'tel', 'inputmode': 'tel', 'autocomplete': 'tel-national',
                'class': 'form-control', 'placeholder': 'Phone number',
            }),
        ), attrs)

    def id_for_label(self, id_):
        return f'{id_}_1' if id_ else ''

    def decompress(self, value):
        if not value:
            return ['IE', '']
        if isinstance(value, (list, tuple)):
            return value
        compact = re.sub(r'[\s().-]', '', value)
        try:
            number = phonenumbers.parse(compact, None)
            region = phonenumbers.region_code_for_number(number)
            if region not in COUNTRY_DETAILS:
                region = phonenumbers.region_code_for_country_code(number.country_code)
            if region in COUNTRY_DETAILS:
                return [region, phonenumbers.national_significant_number(number)]
        except phonenumbers.NumberParseException:
            pass
        # Preserve incomplete saved prefixes, e.g. '+353', without repeating them.
        for code in sorted(phonenumbers.COUNTRY_CODE_TO_REGION_CODE, key=lambda code: -len(str(code))):
            if compact.startswith(f'+{code}'):
                region = phonenumbers.region_code_for_country_code(code)
                if region in COUNTRY_DETAILS:
                    return [region, compact[len(str(code)) + 1:]]
        return ['IE', value]

    def value_from_datadict(self, data, files, name):
        # Accept a previously opened form that still submits the old single field.
        if name in data and f'{name}_0' not in data and f'{name}_1' not in data:
            value = data.get(name, '')
            return self.decompress(value) if value.strip().startswith('+') else ['', value]
        return super().value_from_datadict(data, files, name)


class InternationalPhoneField(forms.MultiValueField):
    def __init__(self, **kwargs):
        super().__init__(fields=(
            forms.ChoiceField(choices=COUNTRY_CHOICES),
            forms.CharField(max_length=40),
        ), widget=InternationalPhoneWidget(), require_all_fields=True,
            error_messages={'required': 'Choose a country code and enter your phone number.'}, **kwargs)

    def compress(self, data_list):
        if not data_list:
            return ''
        region, national = data_list
        if not re.fullmatch(r'\+?[0-9\s().-]+', national):
            raise forms.ValidationError('Enter a phone number using digits, spaces or dashes.')
        try:
            number = phonenumbers.parse(national, region)
        except phonenumbers.NumberParseException:
            raise forms.ValidationError('Enter a complete phone number for the selected country.')
        if number.country_code != COUNTRY_DETAILS[region][1]:
            raise forms.ValidationError('The number uses a different country code. Choose the matching country.')
        if not phonenumbers.is_possible_number(number) or number.extension:
            raise forms.ValidationError('Enter a complete phone number for the selected country.')
        return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
