import re

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from django.db.models import Q

from .forms import StyledFormMixin
from .models import CustomerProfile


def international_phone(value):
    value = re.sub(r'[\s().-]', '', value.strip())
    if not re.fullmatch(r'\+[1-9][0-9]{7,14}', value):
        raise forms.ValidationError('Enter an international phone number, for example +353 89 123 4567.')
    return value


class ContactFields(StyledFormMixin, forms.Form):
    full_name = forms.CharField(max_length=255, label='Full name', widget=forms.TextInput(attrs={'autocomplete': 'name'}))
    email = forms.EmailField(max_length=150, widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    phone = forms.CharField(max_length=40, label='WhatsApp phone number',
                            widget=forms.TextInput(attrs={'type': 'tel', 'autocomplete': 'tel'}),
                            help_text='Include your country code. We use this for your order contact details.')

    def clean_phone(self):
        return international_phone(self.cleaned_data['phone'])

    def clean_email(self):
        return self.cleaned_data['email'].strip().casefold()


class CustomerRegistrationForm(ContactFields):
    password1 = forms.CharField(label='Password', strip=False, widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
                                 help_text=password_validation.password_validators_help_text_html())
    password2 = forms.CharField(label='Confirm password', strip=False, widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}))

    def clean_email(self):
        email = super().clean_email()
        if get_user_model().objects.filter(Q(username__iexact=email) | Q(email__iexact=email)).exists():
            raise forms.ValidationError('An account already uses this email. Please sign in.')
        return email

    def clean(self):
        cleaned = super().clean()
        password = cleaned.get('password1')
        if password and password != cleaned.get('password2'):
            self.add_error('password2', 'The passwords do not match.')
        if password:
            user = get_user_model()(username=cleaned.get('email', ''), email=cleaned.get('email', ''))
            try:
                password_validation.validate_password(password, user=user)
            except forms.ValidationError as exc:
                self.add_error('password1', exc)
        return cleaned

    @transaction.atomic
    def save(self):
        data = self.cleaned_data
        user = get_user_model().objects.create_user(username=data['email'], email=data['email'], password=data['password1'])
        CustomerProfile.objects.create(user=user, full_name=data['full_name'], phone=data['phone'])
        return user


class CustomerLoginForm(StyledFormMixin, AuthenticationForm):
    username = forms.EmailField(label='Email', max_length=150, widget=forms.EmailInput(attrs={'autocomplete': 'username'}))

    def clean_username(self):
        return self.cleaned_data['username'].strip().casefold()


class CustomerContactForm(ContactFields):
    def __init__(self, *args, user, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        if user.email:
            self.fields['email'].disabled = True

    @transaction.atomic
    def save(self):
        if not self.user.email:
            self.user.email = self.cleaned_data['email']
            self.user.save(update_fields=['email'])
        return CustomerProfile.objects.update_or_create(user=self.user, defaults={
            'full_name': self.cleaned_data['full_name'], 'phone': self.cleaned_data['phone'],
        })[0]
