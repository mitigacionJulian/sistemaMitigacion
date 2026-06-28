from django.urls import path

from . import admin_pruebas_views, admin_views

urlpatterns = [
    path("roles/", admin_views.admin_roles_list, name="admin-roles"),
    path("usuarios/", admin_views.admin_usuarios_list_create, name="admin-usuarios"),
    path(
        "usuarios/<int:user_id>/",
        admin_views.admin_usuario_detail,
        name="admin-usuario-detail",
    ),
    path("pruebas/", admin_pruebas_views.admin_pruebas_estado, name="admin-pruebas-estado"),
    path("pruebas/ejecutar/", admin_pruebas_views.admin_pruebas_ejecutar, name="admin-pruebas-ejecutar"),
    path(
        "pruebas/reporte/",
        admin_pruebas_views.admin_pruebas_reporte_imprimible,
        name="admin-pruebas-reporte",
    ),
]
