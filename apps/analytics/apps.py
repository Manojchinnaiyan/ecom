from django.apps import AppConfig


class AnalyticsConfig(
    AppConfig
):  # Make sure this is "AnalyticsConfig", not "AccountsConfig"
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.analytics"
