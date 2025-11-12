#!/bin/sh
set -e

echo "== Starting application startup script =="

if [ -z "$DATABASE_URL" ]; then
  echo "DATABASE_URL is not set — skipping schema reset and running migrations only"
else
  echo "Waiting for database to be reachable..."
  # Try a few times to ensure DB is up
  i=0
  until psql "$DATABASE_URL" -c '\l' >/dev/null 2>&1 || [ $i -ge 12 ]; do
    i=$((i+1))
    echo "  - waiting for DB... attempt $i/12"
    sleep 5
  done

  if [ $i -ge 12 ]; then
    echo "Database not reachable after retries — continuing and hoping for the best"
  else
    echo "Dropping and recreating public schema to ensure clean migrations"
    psql "$DATABASE_URL" -c 'DROP SCHEMA public CASCADE; CREATE SCHEMA public;'
  fi
fi

echo "Running migrations..."
python manage.py migrate --noinput

echo "Creating admin user (if not exists)..."
python manage.py shell < create_admin.py || echo "Admin creation failed or already exists"

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn on 0.0.0.0:8000"
exec gunicorn bgcatalog_project.wsgi:application --bind 0.0.0.0:8000 --workers 2 --access-logfile - --error-logfile - --log-level info
