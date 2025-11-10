import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'bgcatalog_project.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

# Create superuser if it doesn't exist
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='admin@bgcatalog.fly.dev',
        password='admin123'
    )
    print("Superuser created: username='admin', password='admin123'")
else:
    print("Superuser already exists")
