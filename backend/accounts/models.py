from django.conf import settings
from django.db import models
from rest_framework.exceptions import ValidationError as DRFValidationError


class Rol(models.Model):
    codigo = models.CharField(max_length=32, unique=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rol"
        ordering = ["id"]

    def __str__(self):
        return self.nombre


class PerfilUsuario(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column="user_id",
        related_name="perfil",
    )
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, db_column="rol_id")
    telefono = models.CharField(max_length=20, blank=True, null=True)
    organizacion = models.CharField(max_length=255, blank=True, null=True)
    acepta_notificaciones = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "perfil_usuario"

    def __str__(self):
        return f"Perfil({self.user_id})"

    @property
    def telefono_normalizado(self) -> str | None:
        if not self.telefono:
            return None
        try:
            from .phone import normalize_phone_co

            return normalize_phone_co(self.telefono)
        except DRFValidationError:
            return None


class PasswordResetToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_tokens",
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "password_reset_token"
        ordering = ["-created_at"]

    def __str__(self):
        return f"ResetToken({self.user_id})"
