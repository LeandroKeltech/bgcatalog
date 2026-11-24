from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase, override_settings
from django.urls import reverse

from .access import is_admin
from .urls import urlpatterns


@override_settings(STORAGES={'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}})
class AccountAccessTests(TestCase):
    def user(self, username='buyer', **kwargs):
        return get_user_model().objects.create_user(username=username, password='test-password-468!', **kwargs)

    def test_new_accounts_default_to_common_even_with_staff_flag(self):
        for username, flags in [('buyer', {}), ('staff', {'is_staff': True})]:
            user = self.user(username, **flags)
            self.assertEqual(list(user.groups.values_list('name', flat=True)), ['user'])
            self.assertFalse(is_admin(user))

    def test_explicit_superuser_creation_bootstraps_admin(self):
        user = get_user_model().objects.create_superuser('owner', password='test-password-468!')
        self.assertTrue(is_admin(user))
        self.assertFalse(user.groups.filter(name='user').exists())
        user.groups.remove(Group.objects.get(name='admin'))
        user.save()
        self.assertFalse(is_admin(user))
        self.assertTrue(user.groups.filter(name='user').exists())

    def test_group_promotions_removal_and_clear_keep_common_role_consistent(self):
        user = self.user()
        admin, _ = Group.objects.get_or_create(name='admin')
        admin.user_set.add(user)
        self.assertTrue(is_admin(user))
        self.assertFalse(user.groups.filter(name='user').exists())
        admin.user_set.clear()
        self.assertFalse(is_admin(user))
        self.assertTrue(user.groups.filter(name='user').exists())
        user.groups.add(admin)
        user.groups.clear()
        self.assertFalse(is_admin(user))
        self.assertTrue(user.groups.filter(name='user').exists())
        user.groups.clear()
        Group.objects.get(name='user').user_set.clear()
        self.assertTrue(user.groups.filter(name='user').exists())

    def test_all_panel_routes_reject_get_and_post_without_admin_group(self):
        routes = [p for p in urlpatterns if str(p.pattern).startswith('admin-panel/')]
        self.assertTrue(routes, 'Expected administrative routes to exercise access control.')
        accounts = [None, self.user(), self.user('staff', is_staff=True),
                    self.user('super', is_staff=True, is_superuser=True)]
        # A new superuser is bootstrapped, then explicitly demoted for this check.
        accounts[-1].groups.clear()
        for user in accounts:
            self.client.logout()
            if user:
                self.client.force_login(user)
            for route in routes:
                args = ['1' if key == 'bgg_id' else 99999 for key in route.pattern.converters]
                url = reverse(route.name, args=args)
                for method in ('get', 'post'):
                    with self.subTest(user=user, url=url, method=method):
                        self.assertEqual(getattr(self.client, method)(url).status_code, 403 if user else 302)
            self.assertEqual(self.client.get(reverse('admin:index')).status_code, 302)

    def test_admin_group_grants_access_without_staff_and_revocation_is_immediate(self):
        user = self.user()
        user.groups.add(Group.objects.get_or_create(name='admin')[0])
        self.assertFalse(user.is_staff)
        self.assertTrue(self.client.login(username=user.username, password='test-password-468!'))
        for name in ('admin_panel', 'finance_dashboard', 'promotion_list', 'reservation_management', 'admin:index'):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        self.assertContains(self.client.get(reverse('catalog')), 'Admin Panel')
        user.groups.clear()
        self.assertEqual(self.client.get(reverse('admin_panel')).status_code, 403)
        self.assertEqual(self.client.get(reverse('admin:index')).status_code, 302)
        self.assertNotContains(self.client.get(reverse('catalog')), 'Admin Panel')

    def test_admin_login_rejects_common_staff_and_accepts_admin_group(self):
        user = self.user(is_staff=True)
        credentials = {'username': user.username, 'password': 'test-password-468!', 'next': reverse('admin_panel')}
        response = self.client.post(reverse('admin:login'), credentials)
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        user.groups.add(Group.objects.get_or_create(name='admin')[0])
        self.assertEqual(self.client.post(reverse('admin:login'), credentials).status_code, 302)
        user.is_active = False
        user.save()
        self.assertFalse(is_admin(user))
        self.assertEqual(self.client.get(reverse('admin_panel')).status_code, 302)
