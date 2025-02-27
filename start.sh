#!/bin/bash

# Set the correct settings module
export DJANGO_SETTINGS_MODULE=core.settings

# Collect static files
python manage.py collectstatic --noinput || true

# Start Gunicorn
exec gunicorn --bind 0.0.0.0:8000 core.wsgi:application