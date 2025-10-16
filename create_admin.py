"""
Script para criar usuário administrativo
Execute: python manage.py shell < create_admin.py
"""
from django.contrib.auth import get_user_model

User = get_user_model()

# Verificar se o usuário já existe
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser(
        username='admin',
        email='popperl@gmail.com',
        password='bgpeterleandro'
    )
    print("✓ Usuário admin criado com sucesso!")
    print("  Username: admin")
    print("  Senha: bgpeterleandro")
else:
    print("✗ Usuário admin já existe")
