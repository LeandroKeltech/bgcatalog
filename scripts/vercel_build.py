"""Apply schema changes once at production build time, never at request startup."""
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def main():
    if os.environ.get('VERCEL_ENV') != 'production':
        print('Preview build: migrations skipped. Use a separate Neon branch for previews.')
        return
    database_url = os.environ.get('DATABASE_URL_UNPOOLED', '')
    if not database_url.startswith(('postgres://', 'postgresql://')):
        raise SystemExit('Production build requires a direct PostgreSQL DATABASE_URL_UNPOOLED.')

    migration_env = os.environ.copy()
    migration_env['DATABASE_URL'] = database_url

    # Vercel runs collectstatic automatically after this build hook.
    subprocess.run(
        [sys.executable, 'manage.py', 'migrate', '--noinput'],
        cwd=ROOT, check=True, env=migration_env,
    )


if __name__ == '__main__':
    main()
