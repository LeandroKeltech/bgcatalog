"""Check cloud settings in fresh processes without connecting to a database."""
import json
import os
import subprocess
import sys
from unittest.mock import patch

from django.conf import settings
from django.test import SimpleTestCase

from scripts import vercel_build


class VercelConfigurationTests(SimpleTestCase):
    def test_non_vercel_production_also_rejects_missing_secrets_and_sqlite(self):
        result = self.load_settings(VERCEL='0', APP_ENV='production', SECRET_KEY='')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Set a random SECRET_KEY', result.stderr)
        result = self.load_settings(VERCEL='0', APP_ENV='production', DATABASE_URL='sqlite:///db.sqlite3')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('external PostgreSQL', result.stderr)

    def test_production_rejects_unencrypted_database_connection(self):
        result = self.load_settings(DATABASE_URL='postgresql://test:fake@db.invalid/catalog?sslmode=disable')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('must require TLS', result.stderr)

    def load_settings(self, **overrides):
        env = {key: value for key, value in os.environ.items() if key not in (
            'SECRET_KEY', 'DATABASE_URL', 'DEBUG', 'VERCEL_URL',
            'VERCEL_PROJECT_PRODUCTION_URL', 'VERCEL_BRANCH_URL',
            'ALLOWED_HOSTS', 'CSRF_TRUSTED_ORIGINS',
        )}
        env.update(
            VERCEL='1', DEBUG='True', SECRET_KEY='test-secret-' * 8,
            DATABASE_URL='postgresql://test:fake@db.invalid/catalog?sslmode=require',
            VERCEL_URL='bgcatalog-unique.vercel.app',
            VERCEL_PROJECT_PRODUCTION_URL='bgcatalog.vercel.app',
            VERCEL_BRANCH_URL='bgcatalog-main.vercel.app',
        )
        env.update(overrides)
        return subprocess.run(
            [sys.executable, '-c', '''
import json
from bgcatalog_project import settings as s
db = s.DATABASES['default']
print(json.dumps({
    'debug': s.DEBUG, 'hosts': s.ALLOWED_HOSTS,
    'origins': s.CSRF_TRUSTED_ORIGINS,
    'ssl': db['OPTIONS']['sslmode'], 'connection_age': db['CONN_MAX_AGE'],
    'secure_cookies': s.SESSION_COOKIE_SECURE and s.CSRF_COOKIE_SECURE,
    'redirect': s.SECURE_SSL_REDIRECT, 'livereload': s.LIVE_RELOAD_ENABLED,
}))
'''], cwd=settings.BASE_DIR, env=env, capture_output=True, text=True,
        )

    def test_cloud_configuration_supports_admin_csrf_without_debug(self):
        result = self.load_settings(ALLOWED_HOSTS=' games.example.org, ',
                                    CSRF_TRUSTED_ORIGINS=' https://games.example.org, ')
        self.assertEqual(result.returncode, 0, result.stderr)
        config = json.loads(result.stdout)
        self.assertFalse(config['debug'])
        self.assertFalse(config['livereload'])
        self.assertTrue(config['secure_cookies'])
        self.assertTrue(config['redirect'])
        self.assertEqual(config['ssl'], 'require')
        self.assertEqual(config['connection_age'], 0)
        for host in ('games.example.org', 'bgcatalog.vercel.app',
                     'bgcatalog-main.vercel.app', 'bgcatalog-unique.vercel.app'):
            self.assertIn(host, config['hosts'])
            self.assertIn(f'https://{host}', config['origins'])
        self.assertNotIn('', config['hosts'])

    def test_cloud_rejects_missing_or_unsafe_secret(self):
        for secret in ('', 'short', 'django-insecure-' + 'x' * 60):
            with self.subTest(secret_length=len(secret)):
                result = self.load_settings(SECRET_KEY=secret)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('Set a random SECRET_KEY', result.stderr)

    def test_cloud_rejects_missing_database_and_sqlite(self):
        for url in ('', 'sqlite:///db.sqlite3'):
            with self.subTest(url=url):
                result = self.load_settings(DATABASE_URL=url)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('external PostgreSQL', result.stderr)

    @patch('scripts.vercel_build.subprocess.run')
    def test_preview_build_does_not_migrate_database(self, run):
        with patch.dict(os.environ, {'VERCEL_ENV': 'preview'}):
            vercel_build.main()
        run.assert_not_called()

    @patch('scripts.vercel_build.subprocess.run')
    def test_failed_migration_aborts_production_build(self, run):
        run.side_effect = subprocess.CalledProcessError(1, 'migrate')
        with patch.dict(os.environ, {
            'VERCEL_ENV': 'production',
            'DATABASE_URL': 'postgresql://test:fake@db.invalid/catalog',
            'DATABASE_URL_UNPOOLED': 'postgresql://test:fake@direct.invalid/catalog',
        }):
            with self.assertRaises(subprocess.CalledProcessError):
                vercel_build.main()

    @patch('scripts.vercel_build.subprocess.run')
    def test_migrations_use_direct_connection_without_changing_runtime_url(self, run):
        pooled = 'postgresql://test:fake@db-pooler.invalid/catalog'
        direct = 'postgresql://test:fake@db.invalid/catalog'
        with patch.dict(os.environ, {
            'VERCEL_ENV': 'production', 'DATABASE_URL': pooled,
            'DATABASE_URL_UNPOOLED': direct,
        }):
            vercel_build.main()
            self.assertEqual(os.environ['DATABASE_URL'], pooled)
        self.assertEqual(run.call_args.kwargs['env']['DATABASE_URL'], direct)

    @patch('scripts.vercel_build.subprocess.run')
    def test_production_build_requires_direct_database_url(self, run):
        with patch.dict(os.environ, {
            'VERCEL_ENV': 'production', 'DATABASE_URL_UNPOOLED': '',
        }):
            with self.assertRaises(SystemExit):
                vercel_build.main()
        run.assert_not_called()
