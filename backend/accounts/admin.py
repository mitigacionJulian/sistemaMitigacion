from django.contrib import admin

from .models import PasswordResetToken, PerfilUsuario, Rol


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("id", "codigo", "nombre", "activo")
    search_fields = ("codigo", "nombre")


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "rol", "telefono", "organizacion")
    list_filter = ("rol",)


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "created_at", "expires_at", "used_at")
    search_fields = ("user__username", "token")
    readonly_fields = ("token", "created_at")
