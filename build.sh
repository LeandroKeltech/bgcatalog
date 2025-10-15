#!/usr/bin/env bash
# exit on error
set -o errexit

echo "==== Installing dependencies ===="
pip install --upgrade pip
pip install -r requirements.txt

echo "==== Collecting static files ===="
python manage.py collectstatic --no-input

echo "==== Running migrations ===="
python manage.py migrate --no-input --verbosity 2

echo "==== Creating tables if needed ===="
python manage.py migrate catalog --no-input --verbosity 2

echo "==== Build completed successfully ===="
