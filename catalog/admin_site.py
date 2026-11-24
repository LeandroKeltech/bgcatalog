from django.contrib.admin import AdminSite
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError

from .access import is_admin


class GroupAdminAuthenticationForm(AuthenticationForm):
    def confirm_login_allowed(self, user):
        super().confirm_login_allowed(user)
        if not is_admin(user):
            raise ValidationError(self.error_messages['invalid_login'], code='invalid_login',
                                  params={'username': self.username_field.verbose_name})


class GroupAdminSite(AdminSite):
    login_form = GroupAdminAuthenticationForm

    def has_permission(self, request):
        return is_admin(request.user)
