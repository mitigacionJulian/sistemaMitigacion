from django.contrib.auth.hashers import make_password
from django.db import migrations


def seed_admin_user(apps, schema_editor):
    User = apps.get_model("auth", "User")
    Rol = apps.get_model("accounts", "Rol")
    PerfilUsuario = apps.get_model("accounts", "PerfilUsuario")

    rol = Rol.objects.filter(codigo="administrador").first()
    if rol is None:
        return

    user, created = User.objects.get_or_create(
        username="admin",
        defaults={
            "email": "admin@vialdata.local",
            "password": make_password("AdminUSB2026!"),
            "first_name": "Administrador",
            "last_name": "Sistema",
            "is_active": True,
            "is_staff": False,
            "is_superuser": False,
        },
    )
    if not created:
        return

    PerfilUsuario.objects.create(
        user=user,
        rol=rol,
        telefono="573000000001",
        organizacion="Universidad de San Buenaventura",
    )


def unseed_admin_user(apps, schema_editor):
    User = apps.get_model("auth", "User")
    User.objects.filter(username="admin").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0004_alter_perfilusuario_telefono"),
    ]

    operations = [
        migrations.RunPython(seed_admin_user, unseed_admin_user),
    ]
