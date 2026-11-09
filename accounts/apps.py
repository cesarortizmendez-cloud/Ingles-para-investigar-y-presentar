from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"
    verbose_name = "Cuentas y perfil"

    def ready(self):
        from . import signals  # noqa: F401
