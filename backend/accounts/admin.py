from django.contrib import admin

from .models import PerfilUsuario, Rol


@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ("id", "codigo", "nombre", "activo")
    search_fields = ("codigo", "nombre")


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "rol", "organizacion")
    list_filter = ("rol",)
