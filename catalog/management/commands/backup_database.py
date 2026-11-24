"""Create a consistent backup without putting credentials in process arguments."""
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
from contextlib import closing

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Back up the database to a NEW private file; PostgreSQL requires pg_dump.'

    def add_arguments(self, parser):
        parser.add_argument('--output', required=True)

    def handle(self, *args, **options):
        output = Path(options['output']).resolve()
        for public in (settings.STATIC_ROOT, settings.MEDIA_ROOT, settings.BASE_DIR / 'catalog' / 'static'):
            if output.is_relative_to(Path(public).resolve()):
                raise CommandError('Backups must be stored outside web-served directories.')
        if output.exists():
            raise CommandError('The backup destination already exists. Choose a new filename.')
        db = settings.DATABASES['default']
        output.parent.mkdir(parents=True, exist_ok=True)
        # Exclusive creation prevents overwriting existing files or following a
        # destination symlink. Restrictive permissions apply on POSIX systems.
        fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            if db['ENGINE'].endswith('sqlite3'):
                os.close(fd)
                fd = None
                with closing(sqlite3.connect(db['NAME'])) as source, closing(sqlite3.connect(output)) as target:
                    source.backup(target)
                    result = target.execute('PRAGMA integrity_check').fetchone()[0]
                    if result != 'ok':
                        raise CommandError('Backup integrity check failed.')
            elif db['ENGINE'].endswith('postgresql'):
                binary = shutil.which('pg_dump')
                if not binary:
                    raise CommandError('Install the PostgreSQL client tools (pg_dump) before backing up.')
                env = os.environ.copy()
                env.update(PGHOST=str(db['HOST']), PGPORT=str(db['PORT'] or 5432),
                           PGDATABASE=str(db['NAME']), PGUSER=str(db['USER']),
                           PGPASSWORD=str(db['PASSWORD']), PGCONNECT_TIMEOUT='15')
                for key in ('sslmode', 'sslrootcert', 'sslcert', 'sslkey'):
                    if key in db.get('OPTIONS', {}):
                        env['PG' + key.upper()] = str(db['OPTIONS'][key])
                with os.fdopen(fd, 'wb') as stream:
                    fd = None
                    result = subprocess.run([binary, '--format=custom', '--no-owner', '--no-acl'],
                                            env=env, stdout=stream, stderr=subprocess.PIPE, check=False)
                if result.returncode:
                    raise CommandError('pg_dump failed; check connectivity, credentials and client/server versions.')
                if output.stat().st_size == 0:
                    raise CommandError('The database backup was empty.')
            else:
                raise CommandError('Unsupported database backend.')
        except Exception:
            if fd is not None:
                os.close(fd)
            output.unlink(missing_ok=True)
            raise
        self.stdout.write(self.style.SUCCESS(f'Backup created: {output}'))
