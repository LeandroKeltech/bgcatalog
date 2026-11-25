from django import forms
from django.contrib.auth import authenticate, get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import MinimumLengthValidator, CommonPasswordValidator
from django.db import transaction
from django.db.models import Q
from django.views.decorators.debug import sensitive_variables

from .forms import StyledFormMixin
from .models import CustomerProfile
from .phone_fields import InternationalPhoneField


CUSTOMER_PASSWORD_VALIDATORS = [MinimumLengthValidator(min_length=6), CommonPasswordValidator()]


class GuestCheckoutForm(StyledFormMixin, forms.Form):
    email = forms.EmailField(max_length=150, widget=forms.EmailInput(attrs={
        'autocomplete': 'email', 'placeholder': 'you@example.com',
    }))

    def clean_email(self):
        return self.cleaned_data['email'].strip().casefold()


class ContactFields(StyledFormMixin, forms.Form):
    full_name = forms.CharField(max_length=255, label='Full name', widget=forms.TextInput(attrs={'autocomplete': 'name'}))
    email = forms.EmailField(max_length=150, widget=forms.EmailInput(attrs={'autocomplete': 'email'}))
    phone = InternationalPhoneField(label='WhatsApp phone number',
                                    help_text='Select your country code and enter your local number. Used for your order contact details.')

    def clean_email(self):
        return self.cleaned_data['email'].strip().casefold()


class CustomerRegistrationForm(ContactFields):
    password1 = forms.CharField(label='Password', strip=False, widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
                                 help_text=password_validation.password_validators_help_text_html(CUSTOMER_PASSWORD_VALIDATORS))
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
                password_validation.validate_password(password, user=user, password_validators=CUSTOMER_PASSWORD_VALIDATORS)
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
    error_messages = {
        'invalid_login': 'The email or password is incorrect. Please try again.',
        'inactive': 'This account is inactive. Please contact the shop for help.',
    }
    username = forms.EmailField(
        label='Email', max_length=150,
        widget=forms.EmailInput(attrs={
            'autocomplete': 'username', 'placeholder': 'you@example.com',
            'inputmode': 'email', 'autocapitalize': 'none', 'spellcheck': 'false',
        }),
        error_messages={'required': 'Enter your email address.', 'invalid': 'Enter a valid email address.'},
    )
    password = forms.CharField(
        label='Password', strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'placeholder': 'Enter your password'}),
        error_messages={'required': 'Enter your password.'},
    )

    def clean_username(self):
        return self.cleaned_data['username'].strip().casefold()

    @sensitive_variables()
    def clean(self):
        email = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if email is not None and password:
            user_model = get_user_model()
            matches = list(user_model._default_manager.filter(email__iexact=email)
                           .only(user_model.USERNAME_FIELD)[:2])
            if len(matches) != 1:
                # Match the password-hashing work for unknown or ambiguous emails.
                user_model().set_password(password)
                raise self.get_invalid_login_error()
            self.user_cache = authenticate(
                self.request, username=matches[0].get_username(), password=password,
            )
            if self.user_cache is None:
                raise self.get_invalid_login_error()
            self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data


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
