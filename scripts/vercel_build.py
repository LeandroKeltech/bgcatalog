"""Migrate production or the isolated staging database at build time."""
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def main():
    production = os.environ.get('VERCEL_ENV') == 'production'
    staging = (os.environ.get('VERCEL_ENV') == 'preview'
               and os.environ.get('VERCEL_GIT_COMMIT_REF') == 'staging')
    if not (production or staging):
        print('Non-staging preview: database migrations skipped.')
        return
    database_url = os.environ.get('DATABASE_URL_UNPOOLED', '')
    if not database_url.startswith(('postgres://', 'postgresql://')):
        raise SystemExit('Build requires a direct PostgreSQL DATABASE_URL_UNPOOLED.')

    migration_env = os.environ.copy()
    migration_env['DATABASE_URL'] = database_url

    # Vercel runs collectstatic automatically after this build hook.
    subprocess.run(
        [sys.executable, 'manage.py', 'migrate', '--noinput'],
        cwd=ROOT, check=True, env=migration_env,
    )


if __name__ == '__main__':
    main()
