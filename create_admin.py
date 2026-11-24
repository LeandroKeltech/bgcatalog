import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bgcatalog_project.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

if __name__ == '__main__':
    # Delegate credential handling and password validation to Django.
    from django.core.management import call_command

    call_command('createsuperuser')
