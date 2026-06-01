"""
Registra migraciones Django core en django_migrations sin ejecutar SQL.

Uso tras crear la BD con docs/esquema_base_datos.sql:
  python manage.py sync_migration_history
  python manage.py migrate
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

CORE_MIGRATIONS = [
    ("contenttypes", "0001_initial"),
    ("contenttypes", "0002_remove_content_type_name"),
    ("auth", "0001_initial"),
    ("auth", "0002_alter_permission_name_max_length"),
    ("auth", "0003_alter_user_email_max_length"),
    ("auth", "0004_alter_user_username_opts"),
    ("auth", "0005_alter_user_last_login_null"),
    ("auth", "0006_require_contenttypes_0002"),
    ("auth", "0007_alter_validators_add_error_messages"),
    ("auth", "0008_alter_user_username_max_length"),
    ("auth", "0009_alter_user_last_name_max_length"),
    ("auth", "0010_alter_group_name_max_length"),
    ("auth", "0011_update_proxy_permissions"),
    ("auth", "0012_alter_user_first_name_max_length"),
    ("accounts", "0001_initial"),
    ("accounts", "0002_seed_roles"),
    ("accounts", "0003_password_reset_token"),
    ("accounts", "0004_alter_perfilusuario_telefono"),
    ("admin", "0001_initial"),
    ("admin", "0002_logentry_remove_auto_add"),
    ("admin", "0003_logentry_add_action_flag_choices"),
    ("sessions", "0001_initial"),
]


class Command(BaseCommand):
    help = "Registra migraciones core en django_migrations sin ejecutar SQL."

    def handle(self, *args, **options):
        recorder = MigrationRecorder(connection)
        applied = recorder.applied_migrations()
        added = 0
        for app, name in CORE_MIGRATIONS:
            if (app, name) in applied:
                continue
            recorder.record_applied(app, name)
            added += 1
            self.stdout.write(f"  + {app}.{name}")
        self.stdout.write(
            self.style.SUCCESS(
                f"Listo: {added} migraciones registradas ({len(CORE_MIGRATIONS) - added} ya existían)."
            )
        )
