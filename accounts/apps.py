from django.apps import AppConfig


class AccountsConfig(AppConfig):
    # Preserve the existing accounts primary-key type across Django upgrades.
    default_auto_field = 'django.db.models.AutoField'
    name = 'accounts'
