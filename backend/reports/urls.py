from django.urls import path

from . import views

urlpatterns = [
    path(
        "reportes/preview/",
        views.reporte_preview_view,
        name="reportes-preview",
    ),
    path(
        "reportes/tablero/",
        views.reporte_tablero_view,
        name="reportes-tablero",
    ),
    path(
        "reportes/mapa/",
        views.reporte_mapa_view,
        name="reportes-mapa",
    ),
    path(
        "reportes/predicciones/",
        views.reporte_predicciones_view,
        name="reportes-predicciones",
    ),
]
