#!/usr/bin/env bash
set -e
python manage.py makemigrations
python manage.py migrate --noinput

exec "$@"