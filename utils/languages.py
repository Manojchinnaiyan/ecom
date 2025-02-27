# 3. Multi-language Support
# utils/languages.py
from django.utils.translation import gettext_lazy as _


class LanguageSettings:
    """
    Settings and utilities for multi-language support.
    """

    # Supported languages
    LANGUAGES = [
        ("en", _("English")),
        ("es", _("Spanish")),
        ("fr", _("French")),
        ("de", _("German")),
        ("it", _("Italian")),
        ("pt", _("Portuguese")),
        ("ru", _("Russian")),
        ("zh-hans", _("Simplified Chinese")),
        ("ja", _("Japanese")),
        ("ar", _("Arabic")),
    ]

    # Default language
    DEFAULT_LANGUAGE = "en"

    @staticmethod
    def get_language_choices():
        """
        Get language choices for forms and models.
        """
        return LanguageSettings.LANGUAGES
