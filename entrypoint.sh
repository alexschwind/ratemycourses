#!/usr/bin/env bash
set -e
python manage.py makemigrations
python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec "$@"