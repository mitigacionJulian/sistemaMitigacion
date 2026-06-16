import json

from django.conf import settings
from django.db import DatabaseError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAnalista

from .meta import SECCIONES_VALIDAS, build_report_meta
from .mapa import build_mapa_report_body
from .params import parse_mapa_query, parse_predicciones_query, parse_tablero_query
from .predicciones import build_predicciones_report_body
from .tablero import build_tablero_report_body

REPORTE_PERMS = [IsAuthenticated, IsAnalista]

CUERPO_PLACEHOLDER_FASE_0 = {
    "tipo": "placeholder",
    "mensaje": (
        "Infraestructura de reportes (Fase 0). "
        "El contenido específico de tablero, mapa y predicciones se incorporará en fases posteriores."
    ),
}


def _parse_payload(request) -> tuple[dict | None, Response | None]:
    if request.method == "POST":
        data = request.data if isinstance(request.data, dict) else {}
        seccion = data.get("seccion", "preview")
        titulo = data.get("titulo", "")
        notas = data.get("notas", "")
        filtros = data.get("filtros") or {}
        if not isinstance(filtros, dict):
            return None, Response(
                {"detail": "filtros debe ser un objeto JSON."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return {
            "seccion": seccion,
            "titulo": titulo,
            "notas": notas,
            "filtros": filtros,
        }, None

    seccion = request.query_params.get("seccion", "preview")
    titulo = request.query_params.get("titulo", "")
    notas = request.query_params.get("notas", "")
    filtros_raw = request.query_params.get("filtros", "{}")
    try:
        filtros = json.loads(filtros_raw) if filtros_raw else {}
    except json.JSONDecodeError:
        return None, Response(
            {"detail": "filtros debe ser JSON válido."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not isinstance(filtros, dict):
        return None, Response(
            {"detail": "filtros debe ser un objeto JSON."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return {
        "seccion": seccion,
        "titulo": titulo,
        "notas": notas,
        "filtros": filtros,
    }, None


@api_view(["GET", "POST"])
@permission_classes(REPORTE_PERMS)
def reporte_preview_view(request):
    """
    Vista previa del reporte (Fase 0): metadatos estándar + cuerpo placeholder.
    Solo usuarios con rol analista.
    """
    payload, err = _parse_payload(request)
    if err is not None:
        return err

    seccion = payload["seccion"]
    if seccion not in SECCIONES_VALIDAS:
        return Response(
            {
                "detail": (
                    f"seccion inválida. Valores permitidos: "
                    f"{', '.join(sorted(SECCIONES_VALIDAS))}."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    meta = build_report_meta(
        request,
        seccion=seccion,
        filtros=payload["filtros"],
        titulo=payload["titulo"],
        notas=payload["notas"],
    )
    cuerpo = {
        **CUERPO_PLACEHOLDER_FASE_0,
        "seccion_solicitada": seccion,
    }
    return Response({"meta": meta, "cuerpo": cuerpo})


def _parse_tablero_body(request) -> tuple[dict | None, Response | None]:
    if request.method == "POST":
        data = request.data if isinstance(request.data, dict) else {}
        titulo = data.get("titulo", "")
        notas = data.get("notas", "")
        filtros = data.get("filtros") or {}
        query = data.get("query") or {}
        if not isinstance(filtros, dict):
            return None, Response(
                {"detail": "filtros debe ser un objeto JSON."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(query, dict):
            return None, Response(
                {"detail": "query debe ser un objeto JSON."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return {"titulo": titulo, "notas": notas, "filtros": filtros, "query": query}, None

    titulo = request.query_params.get("titulo", "")
    notas = request.query_params.get("notas", "")
    filtros_raw = request.query_params.get("filtros", "{}")
    try:
        filtros = json.loads(filtros_raw) if filtros_raw else {}
    except json.JSONDecodeError:
        return None, Response(
            {"detail": "filtros debe ser JSON válido."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not isinstance(filtros, dict):
        return None, Response(
            {"detail": "filtros debe ser un objeto JSON."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    query = {
        key: request.query_params.get(key)
        for key in (
            "desde",
            "hasta",
            "comuna_id",
            "barrio_id",
            "clase_incidente_id",
            "territorio",
            "top_n",
        )
        if request.query_params.get(key) not in (None, "")
    }
    return {"titulo": titulo, "notas": notas, "filtros": filtros, "query": query}, None


@api_view(["GET", "POST"])
@permission_classes(REPORTE_PERMS)
def reporte_tablero_view(request):
    """
    Reporte del tablero (Fase 1): KPIs, evolución, día/hora, clase, gravedad y tops.
    Solo usuarios con rol analista.
    """
    payload, err = _parse_tablero_body(request)
    if err is not None:
        return err

    try:
        desde, hasta, filtros_kpi, top_n = parse_tablero_query(payload["query"])
    except (ValueError, TypeError):
        return Response(
            {"detail": "Parámetros de fecha, id o top_n inválidos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        cuerpo = build_tablero_report_body(desde, hasta, filtros_kpi, top_n=top_n)
    except DatabaseError as exc:
        err_payload = {
            "detail": "No se pudo consultar la base de datos para el reporte del tablero.",
            "code": "db_error",
        }
        if settings.DEBUG:
            err_payload["debug"] = str(exc)
        return Response(err_payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    meta = build_report_meta(
        request,
        seccion="tablero",
        filtros=payload["filtros"],
        titulo=payload["titulo"],
        notas=payload["notas"],
    )
    return Response({"meta": meta, "cuerpo": cuerpo})


def _parse_mapa_body(request) -> tuple[dict | None, Response | None]:
    if request.method == "POST":
        data = request.data if isinstance(request.data, dict) else {}
        titulo = data.get("titulo", "")
        notas = data.get("notas", "")
        filtros = data.get("filtros") or {}
        query = data.get("query") or {}
        if not isinstance(filtros, dict):
            return None, Response(
                {"detail": "filtros debe ser un objeto JSON."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(query, dict):
            return None, Response(
                {"detail": "query debe ser un objeto JSON."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return {"titulo": titulo, "notas": notas, "filtros": filtros, "query": query}, None

    return _parse_tablero_body(request)


@api_view(["GET", "POST"])
@permission_classes(REPORTE_PERMS)
def reporte_mapa_view(request):
    """Reporte de mapa (Fase 2): territorio, detalle y hotspots."""
    payload, err = _parse_mapa_body(request)
    if err is not None:
        return err

    try:
        desde, hasta, filtros_kpi, _ = parse_tablero_query(payload["query"])
        mapa_query = parse_mapa_query(payload["query"], filtros_kpi)
    except (ValueError, TypeError):
        return Response(
            {"detail": "Parámetros inválidos para reporte de mapa."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        cuerpo = build_mapa_report_body(desde, hasta, filtros_kpi, mapa_query)
    except DatabaseError as exc:
        err_payload = {
            "detail": "No se pudo consultar la base de datos para el reporte de mapa.",
            "code": "db_error",
        }
        if settings.DEBUG:
            err_payload["debug"] = str(exc)
        return Response(err_payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    meta = build_report_meta(
        request,
        seccion="mapa",
        filtros=payload["filtros"],
        titulo=payload["titulo"],
        notas=payload["notas"],
    )
    return Response({"meta": meta, "cuerpo": cuerpo})


def _parse_predicciones_body(request) -> tuple[dict | None, Response | None]:
    if request.method == "POST":
        data = request.data if isinstance(request.data, dict) else {}
        titulo = data.get("titulo", "")
        notas = data.get("notas", "")
        filtros = data.get("filtros") or {}
        query = data.get("query") or {}
        if not isinstance(filtros, dict):
            return None, Response(
                {"detail": "filtros debe ser un objeto JSON."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(query, dict):
            return None, Response(
                {"detail": "query debe ser un objeto JSON."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return {"titulo": titulo, "notas": notas, "filtros": filtros, "query": query}, None

    titulo = request.query_params.get("titulo", "")
    notas = request.query_params.get("notas", "")
    filtros_raw = request.query_params.get("filtros", "{}")
    try:
        filtros = json.loads(filtros_raw) if filtros_raw else {}
    except json.JSONDecodeError:
        return None, Response(
            {"detail": "filtros debe ser JSON válido."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not isinstance(filtros, dict):
        return None, Response(
            {"detail": "filtros debe ser un objeto JSON."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    query = {
        key: request.query_params.get(key)
        for key in (
            "desde",
            "hasta",
            "comuna_id",
            "barrio_id",
            "clase_incidente_id",
            "territorio",
            "horizonte_meses",
            "modelo_pred",
            "modelo_prop",
            "modelo_carga",
            "variable",
            "ventana_ma",
            "nivel_prioridad",
            "nivel_carga",
            "limite_prioridad",
            "limite_carga",
            "excluir_covid",
            "desglose_clase",
            "desglose_comuna",
            "serie_clase_idx",
            "serie_comuna_idx",
        )
        if request.query_params.get(key) not in (None, "")
    }
    return {"titulo": titulo, "notas": notas, "filtros": filtros, "query": query}, None


@api_view(["GET", "POST"])
@permission_classes(REPORTE_PERMS)
def reporte_predicciones_view(request):
    """Reporte de predicciones (Fase 3): proyecciones y rankings modelados."""
    payload, err = _parse_predicciones_body(request)
    if err is not None:
        return err

    try:
        desde, hasta, filtros_kpi, _ = parse_tablero_query(payload["query"])
        pred_query = parse_predicciones_query(payload["query"])
    except (ValueError, TypeError):
        return Response(
            {"detail": "Parámetros inválidos para reporte de predicciones."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if pred_query.desglose_clase and filtros_kpi.clase_incidente_id is not None:
        return Response(
            {
                "detail": (
                    "desglose_clase no aplica si ya filtró por clase_incidente_id; quite uno de los dos."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if pred_query.desglose_comuna and filtros_kpi.comuna_id is not None:
        return Response(
            {
                "detail": (
                    "desglose_comuna no aplica si ya filtró por comuna_id; quite uno de los dos."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if pred_query.nivel_prioridad == "barrio" and filtros_kpi.barrio_id is not None:
        return Response(
            {"detail": "Con barrio_id fijo el ranking por barrio no aplica; quite el filtro de barrio."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if pred_query.nivel_carga == "barrio" and filtros_kpi.barrio_id is not None:
        return Response(
            {"detail": "Con barrio_id fijo el ranking por barrio no aplica; quite el filtro de barrio."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        cuerpo = build_predicciones_report_body(desde, hasta, filtros_kpi, pred_query)
    except DatabaseError as exc:
        err_payload = {
            "detail": "No se pudo consultar la base de datos para el reporte de predicciones.",
            "code": "db_error",
        }
        if settings.DEBUG:
            err_payload["debug"] = str(exc)
        return Response(err_payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    meta = build_report_meta(
        request,
        seccion="predicciones",
        filtros=payload["filtros"],
        titulo=payload["titulo"],
        notas=payload["notas"],
    )
    return Response({"meta": meta, "cuerpo": cuerpo})
