from django.apps import AppConfig


class CalendarioConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'calendario'

    def ready(self):
        import calendario.signals  # noqa
