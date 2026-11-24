#!/bin/sh
set -e

echo "== Starting application startup script =="

case "$DATABASE_URL" in
postgres://*|postgresql://*)
  echo "Waiting for database to be reachable..."
  # Try a few times to ensure DB is up
  i=0
  until psql "$DATABASE_URL" -c 'SELECT 1' >/dev/null 2>&1 || [ $i -ge 12 ]; do
    i=$((i+1))
    echo "  - waiting for DB... attempt $i/12"
    sleep 5
  done

  if [ $i -ge 12 ]; then
    echo "Database not reachable after retries — aborting startup"
    exit 1
  fi
  ;;
esac

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Starting Gunicorn on 0.0.0.0:8000"
exec gunicorn bgcatalog_project.wsgi:application --bind 0.0.0.0:8000 --workers 2 --access-logfile - --error-logfile - --log-level info
