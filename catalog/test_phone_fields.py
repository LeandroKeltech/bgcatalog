from django import forms
from django.test import SimpleTestCase

from .phone_fields import InternationalPhoneField, InternationalPhoneWidget


class InternationalPhoneTests(SimpleTestCase):
    def test_empty_and_incomplete_saved_numbers_default_to_ireland(self):
        widget = InternationalPhoneWidget()
        for value in ('', None, '+353'):
            with self.subTest(value=value):
                self.assertEqual(widget.decompress(value), ['IE', ''])

    def test_existing_international_numbers_are_split_without_losing_digits(self):
        widget = InternationalPhoneWidget()
        for value, expected in (
            ('+353891234568', ['IE', '891234568']),
            ('+5511912345678', ['BR', '11912345678']),
            ('+442083661177', ['GB', '2083661177']),
            ('+12025550123', ['US', '2025550123']),
            ('+14165550123', ['CA', '4165550123']),
            ('+390236618300', ['IT', '0236618300']),
        ):
            with self.subTest(value=value):
                parts = widget.decompress(value)
                self.assertEqual(parts, expected)
                self.assertEqual(InternationalPhoneField().clean(parts), value)

    def test_national_prefixes_and_formatting_are_normalized_for_storage(self):
        field = InternationalPhoneField()
        for parts, expected in (
            (['IE', '089 123 4568'], '+353891234568'),
            (['IE', '89 123 4568'], '+353891234568'),
            (['IE', '+353 89 123 4568'], '+353891234568'),
            (['BR', '(11) 91234-5678'], '+5511912345678'),
            (['GB', '020 8366 1177'], '+442083661177'),
            (['IT', '02 3661 8300'], '+390236618300'),
        ):
            with self.subTest(parts=parts):
                self.assertEqual(field.clean(parts), expected)

    def test_country_and_complete_number_are_required(self):
        for parts in (['IE', ''], ['', '891234568'], ['IE', '123'], ['IE', 'call me'],
                      ['IE', '+5511912345678'], ['XX', '891234568'], ['IE', '+353891234568 ext 12']):
            with self.subTest(parts=parts), self.assertRaises(forms.ValidationError):
                InternationalPhoneField().clean(parts)

    def test_old_single_field_posts_remain_compatible(self):
        widget = InternationalPhoneWidget()
        self.assertEqual(widget.value_from_datadict({'phone': '+353891234568'}, {}, 'phone'), ['IE', '891234568'])
        # A country must still be supplied when posting only a local number.
        with self.assertRaises(forms.ValidationError):
            InternationalPhoneField().clean(widget.value_from_datadict({'phone': '0891234568'}, {}, 'phone'))

    def test_new_fields_take_precedence_over_a_stale_single_field(self):
        data = {'phone': '+353891234568', 'phone_0': 'BR', 'phone_1': '11912345678'}
        parts = InternationalPhoneWidget().value_from_datadict(data, {}, 'phone')
        self.assertEqual(InternationalPhoneField().clean(parts), '+5511912345678')
