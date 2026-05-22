from django.db import migrations


def seed_roles(apps, schema_editor):
    Rol = apps.get_model("accounts", "Rol")
    datos = [
        ("ciudadano", "Ciudadano", "Usuario general / consulta"),
        ("autoridad", "Autoridad", "Perfil institucional / priorización"),
        ("analista", "Analista", "Análisis y reportes"),
        ("administrador", "Administrador", "Gestión de usuarios y configuración"),
    ]
    for codigo, nombre, descripcion in datos:
        Rol.objects.get_or_create(
            codigo=codigo,
            defaults={"nombre": nombre, "descripcion": descripcion, "activo": True},
        )


def unseed_roles(apps, schema_editor):
    Rol = apps.get_model("accounts", "Rol")
    Rol.objects.filter(
        codigo__in=("ciudadano", "autoridad", "analista", "administrador")
    ).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_roles, unseed_roles),
    ]
