from django.urls import path

from . import admin_views

urlpatterns = [
    path("roles/", admin_views.admin_roles_list, name="admin-roles"),
    path("usuarios/", admin_views.admin_usuarios_list_create, name="admin-usuarios"),
    path(
        "usuarios/<int:user_id>/",
        admin_views.admin_usuario_detail,
        name="admin-usuario-detail",
    ),
]
