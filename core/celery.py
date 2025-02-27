import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE", "core.settings"
)  # Not "core.settings.dev"

app = Celery("ecommerce")

# Use strings as keys to avoid serializing the configuration object
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs
app.autodiscover_tasks()
