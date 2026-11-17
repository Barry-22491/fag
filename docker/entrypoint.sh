#!/bin/sh
set -e

if [ "$(id -u)" = "0" ]; then
    mkdir -p /app/media /app/staticfiles
    chown -R app:app /app/media /app/staticfiles
    exec gosu app "$0" "$@"
fi

if [ "$1" = "gunicorn" ]; then
    python manage.py migrate --noinput
    python manage.py collectstatic --noinput
fi

exec "$@"
