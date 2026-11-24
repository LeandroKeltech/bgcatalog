from django.apps import AppConfig
from django.contrib.admin.apps import AdminConfig


class GroupAdminConfig(AdminConfig):
    default_site = 'catalog.admin_site.GroupAdminSite'


class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'catalog'

    def ready(self):
        from . import signals  # noqa: F401
