"""Vistas de administración: ejecución y reporte de pruebas."""
from __future__ import annotations

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from reports.meta import build_report_meta

from .permissions import IsAdministrador
from .pruebas_reporte import build_pruebas_report_body
from .pruebas_runner import build_status_payload, can_run_tests, start_test_run

ADMIN_PERMS = [IsAdministrador]


@api_view(["GET"])
@permission_classes(ADMIN_PERMS)
def admin_pruebas_estado(request):
    return Response(build_status_payload())


@api_view(["POST"])
@permission_classes(ADMIN_PERMS)
def admin_pruebas_ejecutar(request):
    if not can_run_tests():
        return Response(
            {
                "detail": "La ejecución de pruebas desde la UI está deshabilitada. "
                "Active DJANGO_DEBUG=1 o ALLOW_ADMIN_TEST_RUNNER=1 en desarrollo.",
                "code": "runner_disabled",
            },
            status=status.HTTP_403_FORBIDDEN,
        )
    ok, mensaje, _ = start_test_run(username=getattr(request.user, "username", None))
    payload = build_status_payload()
    payload["mensaje_inicio"] = mensaje
    if not ok:
        return Response({**payload, "detail": mensaje}, status=status.HTTP_409_CONFLICT)
    return Response(payload, status=status.HTTP_202_ACCEPTED)


@api_view(["POST"])
@permission_classes(ADMIN_PERMS)
def admin_pruebas_reporte_imprimible(request):
    """Payload para /reporte/vista (imprimir o guardar PDF)."""
    cuerpo = build_pruebas_report_body()
    if not cuerpo.get("hay_resultados"):
        return Response(
            {
                "detail": "No hay resultados de pruebas. Ejecute primero la suite desde este panel.",
                "code": "sin_resultados",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = request.data if isinstance(request.data, dict) else {}
    titulo = data.get("titulo", "")
    notas = data.get("notas", "")
    return Response(
        {
            "meta": build_report_meta(
                request,
                seccion="pruebas",
                titulo=titulo,
                notas=notas,
                filtros={},
            ),
            "cuerpo": cuerpo,
        }
    )
