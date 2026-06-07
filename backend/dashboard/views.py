from datetime import date, datetime

from django.conf import settings
from django.db import DatabaseError
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from accounts.permissions import IsAnalista

PREDICCIONES_PERMS = [IsAuthenticated, IsAnalista]

from .distribucion_clase_incidente import build_distribucion_clase_incidente_payload
from .distribucion_gravedad import build_distribucion_gravedad_payload
from .evolucion_mensual import build_evolucion_payload
from .incidentes_mapa import MAPA_CAP_SIN_LIMITE, build_incidentes_mapa_payload
from .kpis import FiltrosKpi, build_kpis_payload
from .matriz_dia_hora import build_matriz_dia_hora_payload
from .patrones_temporales_proyectados import (
    build_dia_semana_proyectado_payload,
    build_matriz_dia_hora_proyectada_payload,
)
from .por_dia_semana import build_dia_semana_payload
from .calidad_territorio import build_calidad_territorio_payload
from .choropleth_territorial import (
    build_choropleth_territorial_payload,
    parse_metrica_choropleth,
    parse_nivel_choropleth,
)
from .comunas_geojson import build_comunas_geojson
from .densidad_territorial import build_densidad_territorial_payload, clamp_limite_densidad
from .hotspots import (
    build_hotspots_payload,
    build_hotspots_ranking_payload,
    clamp_limite_celdas,
    clamp_limite_ranking_g06,
    clamp_tamano_celda_m,
    parse_metodo_hotspot,
)
from .territorio_sql import parse_filtro_geojson
from .carga_esperada_espacial import build_carga_espacial_payload
from .carga_esperada_territorial import build_carga_esperada_payload
from .predicciones_mensuales import (
    MA_VENTANA_DEFAULT,
    MA_VENTANA_MAX,
    MA_VENTANA_MIN,
    build_predicciones_mensuales_payload,
)
from .prioridad_territorial import build_prioridad_territorial_payload
from .proporcion_fatales_mensual import build_proporcion_fatales_payload
from .tops import build_tops_payload
from .mapa_detalle import build_mapa_detalle_payload
from .territorio_sql import parse_modo_territorio, parse_modo_punto_critico

# Rango referencia `salida/Mede_Victimas_inci_depurado.xlsx` (si aún no hay filas en `incidente`)
_REF_MIN = date(2014, 1, 1)
_REF_MAX = date(2021, 9, 30)


def _as_date(d) -> date | None:
    if d is None:
        return None
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    return d


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_rango_fechas_view(request):
    """
    Fechas mín/máx en `incidente` y defaults para el tablero:
    periodo actual = 1 ene del último año con datos → última fecha con datos.
    """
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT MIN(fecha_incidente), MAX(fecha_incidente) FROM incidente"
            )
            row = cursor.fetchone()
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo leer el rango de fechas (tabla `incidente` o conexión).",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    dmin = _as_date(row[0]) if row else None
    dmax = _as_date(row[1]) if row else None

    if not dmin or not dmax:
        ultimo_ref = _REF_MAX
        return Response(
            {
                "hay_datos": False,
                "fecha_minima": None,
                "fecha_maxima": None,
                "anio_minimo": None,
                "anio_maximo": None,
                "ultimo_anio_con_datos": ultimo_ref.year,
                "default_desde": date(ultimo_ref.year, 1, 1).isoformat(),
                "default_hasta": ultimo_ref.isoformat(),
                "selector_fecha_min": _REF_MIN.isoformat(),
                "selector_fecha_max": _REF_MAX.isoformat(),
                "referencia_fuente": "Sin registros en `incidente`: defaults al último año del archivo Mede depurado (~2014–2021). Ejecute la carga ETL si corresponde.",
            }
        )

    ultimo_anio = dmax.year
    default_desde = date(ultimo_anio, 1, 1)
    default_hasta = dmax

    return Response(
        {
            "hay_datos": True,
            "fecha_minima": dmin.isoformat(),
            "fecha_maxima": dmax.isoformat(),
            "anio_minimo": dmin.year,
            "anio_maximo": dmax.year,
            "ultimo_anio_con_datos": ultimo_anio,
            "default_desde": default_desde.isoformat(),
            "default_hasta": default_hasta.isoformat(),
            "selector_fecha_min": dmin.isoformat(),
            "selector_fecha_max": dmax.isoformat(),
            "referencia_fuente": None,
        }
    )


def _parse_date(qs, key: str, default):
    raw = qs.get(key)
    if not raw:
        return default
    return date.fromisoformat(raw)


def _optional_int(qs, key: str) -> int | None:
    raw = qs.get(key)
    if raw is None or raw == "":
        return None
    return int(raw)


def _parse_filtros_kpi(qs) -> FiltrosKpi:
    return FiltrosKpi(
        comuna_id=_optional_int(qs, "comuna_id"),
        barrio_id=_optional_int(qs, "barrio_id"),
        clase_incidente_id=_optional_int(qs, "clase_incidente_id"),
        modo_territorio=parse_modo_territorio(qs.get("territorio")),
    )


def _parse_modo_punto(qs) -> str:
    return parse_modo_punto_critico(qs.get("modo_punto") or qs.get("punto_asignacion"))


def _parse_horizonte_meses(qs) -> int:
    raw = qs.get("horizonte_meses") or qs.get("meses")
    if raw is None or raw == "":
        return 3
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return 3
    return max(1, min(12, v))


def _parse_limite_mapa(qs) -> int:
    raw = qs.get("limite")
    if raw is None or raw == "":
        return 10_000
    try:
        v = int(raw)
    except (TypeError, ValueError):
        return 10_000
    if v == 0:
        return 0
    return max(100, min(MAPA_CAP_SIN_LIMITE, v))


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_kpis_view(request):
    """
    KPIs del periodo [desde, hasta] comparados con el mismo intervalo un año antes.

    Query params:
      desde (ISO date), hasta (ISO date) — por defecto 1 ene año actual → hoy.
      comuna_id, barrio_id, clase_incidente_id — filtros opcionales.
    """
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today

    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
    except (ValueError, TypeError):
        return Response(
            {"detail": "Parámetros de fecha o id inválidos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = build_kpis_payload(desde, hasta, filtros)
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo consultar la base de datos (tablas incidente/víctima o conexión PostgreSQL).",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(payload)


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_evolucion_mensual_view(request):
    """
    Serie mensual en [desde, hasta] y comparación por mes con el mismo intervalo un año antes
    (mismos filtros que KPIs).
    """
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today

    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
    except (ValueError, TypeError):
        return Response(
            {"detail": "Parámetros de fecha o id inválidos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = build_evolucion_payload(desde, hasta, filtros)
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo consultar la evolución mensual en la base de datos.",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(payload)


def _parse_modelo_prediccion(qs) -> str:
    raw = (qs.get("modelo") or "ols").strip().lower()
    aliases = {
        "ols": "ols",
        "lineal": "ols",
        "estacional": "estacional",
        "seasonal": "estacional",
        "poisson": "poisson",
        "glm_poisson": "poisson",
        "media_movil": "media_movil",
        "ma": "media_movil",
        "moving_average": "media_movil",
    }
    if raw not in aliases:
        raise ValueError("modelo")
    return aliases[raw]


def _parse_ventana_ma(qs) -> int:
    raw = qs.get("ventana_ma") or qs.get("ventana") or MA_VENTANA_DEFAULT
    try:
        v = int(raw)
    except (TypeError, ValueError):
        raise ValueError("ventana_ma")
    if not (MA_VENTANA_MIN <= v <= MA_VENTANA_MAX):
        raise ValueError("ventana_ma")
    return v


def _parse_variable_prediccion(qs) -> str:
    raw = (qs.get("variable") or "incidentes").strip().lower()
    aliases = {
        "incidentes": "incidentes",
        "incidente": "incidentes",
        "victimas": "victimas",
        "victima": "victimas",
        "victimas_fatales": "victimas_fatales",
        "fatales": "victimas_fatales",
        "fatal": "victimas_fatales",
    }
    if raw not in aliases:
        raise ValueError("variable")
    return aliases[raw]


def _parse_desglose_clase(qs) -> bool:
    raw = (qs.get("desglose_clase") or "").strip().lower()
    return raw in ("1", "true", "si", "sí", "yes")


def _parse_excluir_covid(qs) -> bool:
    raw = (qs.get("excluir_covid") or "").strip().lower()
    return raw in ("1", "true", "si", "sí", "yes")


@api_view(["GET"])
@permission_classes(PREDICCIONES_PERMS)
def dashboard_predicciones_mensuales_view(request):
    """
    Proyección mensual (Fase A).

    Query:
      horizonte_meses (1–12, default 3);
      modelo: ols | estacional | poisson | media_movil (default ols);
      ventana_ma (2–12, default 3; solo media_movil);
      variable: incidentes | victimas | victimas_fatales (default incidentes);
      desglose_clase: 1 para series por clase (solo si no hay clase_incidente_id);
      excluir_covid: 1 para no usar mar–ago 2020 en el ajuste (siguen en el gráfico).
    """
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today

    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
        horizonte = _parse_horizonte_meses(request.GET)
        modelo = _parse_modelo_prediccion(request.GET)
        variable = _parse_variable_prediccion(request.GET)
        ventana_ma = _parse_ventana_ma(request.GET)
        desglose_clase = _parse_desglose_clase(request.GET)
        excluir_covid = _parse_excluir_covid(request.GET)
    except (ValueError, TypeError):
        return Response(
            {
                "detail": (
                    "Parámetros inválidos. modelo: ols|estacional|poisson|media_movil; "
                    "ventana_ma: 2–12; variable: incidentes|victimas|victimas_fatales."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desglose_clase and filtros.clase_incidente_id is not None:
        return Response(
            {
                "detail": "desglose_clase no aplica si ya filtró por clase_incidente_id; quite uno de los dos.",
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = build_predicciones_mensuales_payload(
            desde,
            hasta,
            filtros,
            horizonte,
            modelo=modelo,
            variable=variable,
            desglose_clase=desglose_clase,
            excluir_covid=excluir_covid,
            ventana_ma=ventana_ma,
        )
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo consultar la base de datos para predicciones mensuales.",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(payload)


def _parse_nivel_prioridad(qs) -> str:
    raw = (qs.get("nivel") or "comuna").strip().lower()
    if raw not in ("comuna", "barrio"):
        raise ValueError("nivel")
    return raw


@api_view(["GET"])
@permission_classes(PREDICCIONES_PERMS)
def dashboard_prioridad_territorial_view(request):
    """
    P05 — Índice de prioridad compuesto por comuna o barrio.

    Query: nivel=comuna|barrio (default comuna), limite (1–50, default 15),
    excluir_covid (default 1 para tendencia), mismos filtros de fecha/territorio.
    """
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today

    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
        nivel = _parse_nivel_prioridad(request.GET)
        limite = _optional_int(request.GET, "limite") or 15
        excluir_covid = _parse_excluir_covid(request.GET)
    except (ValueError, TypeError):
        return Response(
            {"detail": "Parámetros inválidos. nivel: comuna|barrio; limite: 1–50."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if nivel == "barrio" and filtros.barrio_id is not None:
        return Response(
            {"detail": "Con barrio_id fijo el ranking por barrio no aplica; quite el filtro de barrio."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = build_prioridad_territorial_payload(
            desde,
            hasta,
            filtros,
            nivel=nivel,
            limite=limite,
            excluir_covid=excluir_covid,
        )
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo calcular la prioridad territorial.",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(payload)


def _parse_modelo_proporcion(qs) -> str:
    raw = (qs.get("modelo") or "estacional").strip().lower()
    aliases = {
        "ols": "ols",
        "lineal": "ols",
        "logistica": "logistica",
        "logistic": "logistica",
        "estacional": "estacional",
        "seasonal": "estacional",
        "media_movil": "media_movil",
        "ma": "media_movil",
        "moving_average": "media_movil",
    }
    if raw not in aliases:
        raise ValueError("modelo")
    return aliases[raw]


def _parse_desglose_comuna(qs) -> bool:
    raw = (qs.get("desglose_comuna") or "").strip().lower()
    return raw in ("1", "true", "si", "sí", "yes")


def _parse_modelo_carga(qs) -> str:
    raw = (qs.get("modelo") or "estacional").strip().lower()
    aliases = {
        "ols": "ols",
        "lineal": "ols",
        "estacional": "estacional",
        "seasonal": "estacional",
        "media_movil": "media_movil",
        "ma": "media_movil",
        "moving_average": "media_movil",
    }
    if raw not in aliases:
        raise ValueError("modelo")
    return aliases[raw]


@api_view(["GET"])
@permission_classes(PREDICCIONES_PERMS)
def dashboard_proporcion_fatales_mensual_view(request):
    """
    P07 — Proporción mensual de víctimas fatales (% sobre víctimas del mes).

    Query: modelo=ols|logistica|estacional|media_movil (default estacional), horizonte_meses (1–12),
    ventana_ma (2–12, solo media_movil), desglose_comuna=1 (top 10 comunas si no hay comuna_id), excluir_covid.
    """
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today

    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
        horizonte = _parse_horizonte_meses(request.GET)
        modelo = _parse_modelo_proporcion(request.GET)
        ventana_ma = _parse_ventana_ma(request.GET)
        desglose_comuna = _parse_desglose_comuna(request.GET)
        excluir_covid = _parse_excluir_covid(request.GET)
    except (ValueError, TypeError):
        return Response(
            {
                "detail": (
                    "Parámetros inválidos. modelo: ols|logistica|estacional|media_movil; "
                    "ventana_ma: 2–12; horizonte_meses: 1–12."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desglose_comuna and filtros.comuna_id is not None:
        return Response(
            {
                "detail": (
                    "desglose_comuna no aplica si ya filtró por comuna_id; quite uno de los dos."
                ),
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = build_proporcion_fatales_payload(
            desde,
            hasta,
            filtros,
            horizonte_meses=horizonte,
            modelo=modelo,
            excluir_covid=excluir_covid,
            desglose_comuna=desglose_comuna,
            ventana_ma=ventana_ma,
        )
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo consultar la proporción de víctimas fatales.",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(payload)


@api_view(["GET"])
@permission_classes(PREDICCIONES_PERMS)
def dashboard_carga_esperada_territorial_view(request):
    """
    P08 — Categoría alto / medio / bajo de carga esperada por comuna o barrio.

    Query: nivel=comuna|barrio, limite (1–50), horizonte_meses, modelo=ols|estacional|media_movil,
    ventana_ma (2–12), excluir_covid; mismos filtros de fecha/territorio.
    """
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today

    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
        nivel = _parse_nivel_prioridad(request.GET)
        limite = _optional_int(request.GET, "limite") or 20
        horizonte = _parse_horizonte_meses(request.GET)
        modelo = _parse_modelo_carga(request.GET)
        ventana_ma = _parse_ventana_ma(request.GET)
        excluir_covid = _parse_excluir_covid(request.GET)
    except (ValueError, TypeError):
        return Response(
            {
                "detail": (
                    "Parámetros inválidos. nivel: comuna|barrio; "
                    "modelo: ols|estacional|media_movil; ventana_ma: 2–12; limite: 1–50."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if nivel == "barrio" and filtros.barrio_id is not None:
        return Response(
            {"detail": "Con barrio_id fijo el ranking por barrio no aplica; quite el filtro de barrio."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = build_carga_esperada_payload(
            desde,
            hasta,
            filtros,
            nivel=nivel,
            horizonte_meses=horizonte,
            modelo=modelo,
            excluir_covid=excluir_covid,
            limite=limite,
            ventana_ma=ventana_ma,
        )
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo calcular la carga esperada territorial.",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(payload)


def _parse_tipo_espacial(qs) -> str:
    raw = (qs.get("tipo") or "series_territorial").strip().lower()
    aliases = {
        "series": "series_territorial",
        "series_territorial": "series_territorial",
        "p09": "series_territorial",
        "p10": "series_territorial",
        "ranking_via": "ranking_via",
        "via": "ranking_via",
        "p11_via": "ranking_via",
        "ranking_punto": "ranking_punto",
        "punto": "ranking_punto",
        "punto_critico": "ranking_punto",
        "p11_punto": "ranking_punto",
    }
    if raw not in aliases:
        raise ValueError("tipo")
    return aliases[raw]


@api_view(["GET"])
@permission_classes(PREDICCIONES_PERMS)
def dashboard_carga_esperada_espacial_view(request):
    """
    Fase C — series por comuna/barrio (legacy API). P11 omitido del producto.

    Query: tipo=series_territorial|ranking_via|ranking_punto; nivel=comuna|barrio (series);
    limite (1–15, default 8), horizonte_meses, modelo=ols|estacional, entidad_id (opcional).
    """
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today

    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
        tipo = _parse_tipo_espacial(request.GET)
        nivel = _parse_nivel_prioridad(request.GET)
        limite = _optional_int(request.GET, "limite") or 8
        horizonte = _parse_horizonte_meses(request.GET)
        modelo = _parse_modelo_carga(request.GET)
        ventana_ma = _parse_ventana_ma(request.GET)
        excluir_covid = _parse_excluir_covid(request.GET)
        entidad_id = _optional_int(request.GET, "entidad_id")
        modo_punto = _parse_modo_punto(request.GET)
    except (ValueError, TypeError):
        return Response(
            {
                "detail": (
                    "Parámetros inválidos. tipo: series_territorial|ranking_via|ranking_punto; "
                    "modelo: ols|estacional|media_movil; ventana_ma: 2–12; limite: 1–15."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if tipo == "series_territorial" and nivel == "barrio" and filtros.barrio_id is not None:
        return Response(
            {"detail": "Con barrio_id fijo el desglose por barrios no aplica."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = build_carga_espacial_payload(
            desde,
            hasta,
            filtros,
            tipo=tipo,
            nivel=nivel,
            horizonte_meses=horizonte,
            modelo=modelo,
            excluir_covid=excluir_covid,
            limite=limite,
            entidad_id=entidad_id,
            modo_punto=modo_punto,
            ventana_ma=ventana_ma,
        )
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo calcular la carga espacial proyectada.",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(payload)


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_por_dia_semana_view(request):
    """
    Serie por día de la semana en [desde, hasta] + comparación con año anterior.
    Incluye participación en el total semanal de incidentes y semáforo de concentración vs. reparto uniforme.
    """
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today

    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
    except (ValueError, TypeError):
        return Response(
            {"detail": "Parámetros de fecha o id inválidos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = build_dia_semana_payload(desde, hasta, filtros)
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo consultar la serie por día de la semana en la base de datos.",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(payload)


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_matriz_dia_hora_view(request):
    """
    Matriz día/hora en [desde, hasta] y comparación con mismo intervalo del año anterior.
    """
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today

    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
    except (ValueError, TypeError):
        return Response(
            {"detail": "Parámetros de fecha o id inválidos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = build_matriz_dia_hora_payload(desde, hasta, filtros)
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo consultar la matriz día/hora en la base de datos.",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(payload)


@api_view(["GET"])
@permission_classes(PREDICCIONES_PERMS)
def dashboard_matriz_dia_hora_proyectada_view(request):
    """
    P12 — Matriz día×hora con incidentes proyectados en el horizonte.

    Query: horizonte_meses (1–12), modelo=ols|estacional, excluir_covid; filtros de fecha/territorio.
    """
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today

    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
        horizonte = _parse_horizonte_meses(request.GET)
        modelo = _parse_modelo_carga(request.GET)
        ventana_ma = _parse_ventana_ma(request.GET)
        excluir_covid = _parse_excluir_covid(request.GET)
    except (ValueError, TypeError):
        return Response(
            {
                "detail": (
                    "Parámetros inválidos. horizonte_meses: 1–12; "
                    "modelo: ols|estacional|media_movil; ventana_ma: 2–12."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = build_matriz_dia_hora_proyectada_payload(
            desde,
            hasta,
            filtros,
            horizonte_meses=horizonte,
            modelo=modelo,
            excluir_covid=excluir_covid,
            ventana_ma=ventana_ma,
        )
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo calcular la matriz día/hora proyectada.",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(payload)


@api_view(["GET"])
@permission_classes(PREDICCIONES_PERMS)
def dashboard_por_dia_semana_proyectado_view(request):
    """
    P13 — Incidentes proyectados por día de semana en el horizonte.

    Query: horizonte_meses (1–12), modelo=ols|estacional, excluir_covid; filtros de fecha/territorio.
    """
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today

    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
        horizonte = _parse_horizonte_meses(request.GET)
        modelo = _parse_modelo_carga(request.GET)
        ventana_ma = _parse_ventana_ma(request.GET)
        excluir_covid = _parse_excluir_covid(request.GET)
    except (ValueError, TypeError):
        return Response(
            {
                "detail": (
                    "Parámetros inválidos. horizonte_meses: 1–12; "
                    "modelo: ols|estacional|media_movil; ventana_ma: 2–12."
                )
            },
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = build_dia_semana_proyectado_payload(
            desde,
            hasta,
            filtros,
            horizonte_meses=horizonte,
            modelo=modelo,
            excluir_covid=excluir_covid,
            ventana_ma=ventana_ma,
        )
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo calcular la proyección por día de semana.",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(payload)


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_distribucion_gravedad_view(request):
    """
    Distribución por gravedad (víctimas) comparando periodo actual vs año anterior.
    """
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today
    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
    except (ValueError, TypeError):
        return Response({"detail": "Parámetros de fecha o id inválidos."}, status=status.HTTP_400_BAD_REQUEST)

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        payload = build_distribucion_gravedad_payload(desde, hasta, filtros)
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo consultar la distribución por gravedad en la base de datos.",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response(payload)


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_distribucion_clase_incidente_view(request):
    """
    Incidentes por clase de incidente: periodo actual vs mismo intervalo del año anterior.
    """
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today
    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
    except (ValueError, TypeError):
        return Response({"detail": "Parámetros de fecha o id inválidos."}, status=status.HTTP_400_BAD_REQUEST)

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        payload = build_distribucion_clase_incidente_payload(desde, hasta, filtros)
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo consultar la distribución por clase de incidente en la base de datos.",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response(payload)


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_tops_view(request):
    """
    Rankings: top sexo, edad, condición, comuna, barrio (víctimas en el periodo).
    Query params: desde, hasta, comuna_id, barrio_id, clase_incidente_id, top_n (1–25, default 10).
    """
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today
    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
        top_n = _optional_int(request.GET, "top_n")
        if top_n is None:
            top_n = 10
    except (ValueError, TypeError):
        return Response({"detail": "Parámetros de fecha, id o top_n inválidos."}, status=status.HTTP_400_BAD_REQUEST)

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )
    try:
        payload = build_tops_payload(desde, hasta, filtros, limite=top_n)
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudieron calcular los rankings en la base de datos.",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    return Response(payload)


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_incidentes_mapa_view(request):
    """
    Puntos de incidentes con coordenadas para mapa (muestra acotada por `limite`).

    Query `limite`:
    - omitido: 10000;
    - 100–100000: tope fijo de filas devueltas (orden más reciente primero);
    - 0: equivale a cargar hasta min(total_en_rango, 100000) (ver meta).

    Mismos filtros de fecha y territorio que KPIs.
    """
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today

    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
        limite = _parse_limite_mapa(request.GET)
    except (ValueError, TypeError):
        return Response(
            {"detail": "Parámetros de fecha, id o limite inválidos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = build_incidentes_mapa_payload(desde, hasta, filtros, limite)
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo consultar la base de datos para el mapa de incidentes.",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(payload)


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_hotspots_cuadricula_view(request):
    """
    F4 / P14 — Hotspots espaciales (cuadrícula PostGIS, opcional polígono).

    Query: desde, hasta, filtros territorio, metodo=cuadricula|area,
    tamano_celda_m (50–2000, default 300), limite_celdas (1–2000, default 800),
    geojson (geometría Polygon/MultiPolygon para modo area).
    """
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today

    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
        metodo = parse_metodo_hotspot(request.GET.get("metodo"))
        tamano_celda_m = clamp_tamano_celda_m(
            request.GET.get("tamano_celda_m"), metodo=metodo
        )
        limite_celdas = clamp_limite_celdas(
            int(request.GET["limite_celdas"]) if request.GET.get("limite_celdas") else None
        )
        geojson = parse_filtro_geojson(request.GET.get("geojson"))
    except (ValueError, TypeError):
        return Response(
            {"detail": "Parámetros de fecha, id, geojson o hotspots inválidos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = build_hotspots_payload(
            desde,
            hasta,
            filtros,
            metodo=metodo,
            tamano_celda_m=tamano_celda_m,
            limite_celdas=limite_celdas,
            geojson=geojson,
        )
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo consultar hotspots espaciales (PostGIS requerido).",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(payload)


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_hotspots_ranking_view(request):
    """F5 / G06 — Top celdas calientes (ranking tabular)."""
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today

    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
        tamano_celda_m = clamp_tamano_celda_m(request.GET.get("tamano_celda_m"))
        limite = clamp_limite_ranking_g06(
            int(request.GET["limite"]) if request.GET.get("limite") else None
        )
        orden = request.GET.get("orden") or "densidad"
    except (ValueError, TypeError):
        return Response(
            {"detail": "Parámetros de fecha, id o ranking inválidos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = build_hotspots_ranking_payload(
            desde,
            hasta,
            filtros,
            tamano_celda_m=tamano_celda_m,
            limite=limite,
            orden=orden,
        )
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo consultar ranking de celdas (PostGIS requerido).",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(payload)


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_densidad_territorial_view(request):
    """F5 / G01–G02 — Densidad incidentes por km² y ratio vs. ciudad."""
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today

    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
        raw_nivel = (request.GET.get("nivel") or "comuna").strip().lower()
        nivel = "barrio" if raw_nivel == "barrio" else "comuna"
        limite = clamp_limite_densidad(
            int(request.GET["limite"]) if request.GET.get("limite") else None
        )
    except (ValueError, TypeError):
        return Response(
            {"detail": "Parámetros de fecha, id o densidad inválidos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = build_densidad_territorial_payload(
            desde,
            hasta,
            filtros,
            nivel=nivel,
            limite=limite,
        )
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo consultar densidad territorial (PostGIS requerido).",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(payload)


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_mapa_detalle_view(request):
    """
    Coroplética + puntos en una sola respuesta (modo Detalle del mapa inicio).

    Query: desde, hasta, filtros territorio, nivel, metrica, limite (igual que incidentes-mapa).
    """
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today

    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
        nivel = parse_nivel_choropleth(request.GET.get("nivel"))
        metrica = parse_metrica_choropleth(request.GET.get("metrica"))
        limite = _parse_limite_mapa(request.GET)
    except (ValueError, TypeError):
        return Response(
            {"detail": "Parámetros de fecha, filtro o limite inválidos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = build_mapa_detalle_payload(
            desde,
            hasta,
            filtros,
            nivel=nivel,
            metrica=metrica,
            limite=limite,
        )
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo consultar el mapa detalle (PostGIS requerido).",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(payload)


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_choropleth_territorial_view(request):
    """Coroplética — GeoJSON con concentración por comuna o barrio (G01 en mapa)."""
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today

    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
        nivel = parse_nivel_choropleth(request.GET.get("nivel"))
        metrica = parse_metrica_choropleth(request.GET.get("metrica"))
    except (ValueError, TypeError):
        return Response(
            {"detail": "Parámetros de fecha o filtro inválidos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "El rango es inválido: 'desde' no puede ser posterior a 'hasta'."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = build_choropleth_territorial_payload(
            desde,
            hasta,
            filtros,
            nivel=nivel,
            metrica=metrica,
        )
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo consultar la coroplética territorial (PostGIS requerido).",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(payload)


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_calidad_territorio_view(request):
    """
    G03 / F2.4 — Calidad geografica: discrepancia comuna/barrio registro vs poligono.

    Query params: desde, hasta, comuna_id, barrio_id, clase_incidente_id, limite_ejemplos (default 10).
    """
    today = date.today()
    default_desde = date(today.year, 1, 1)
    default_hasta = today

    try:
        desde = _parse_date(request.GET, "desde", default_desde)
        hasta = _parse_date(request.GET, "hasta", default_hasta)
        filtros = _parse_filtros_kpi(request.GET)
        raw_lim = request.GET.get("limite_ejemplos")
        limite_ejemplos = 10 if raw_lim is None else max(0, min(50, int(raw_lim)))
    except (ValueError, TypeError):
        return Response(
            {"detail": "Parametros de fecha o filtro invalidos."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if desde > hasta:
        return Response(
            {"detail": "desde no puede ser posterior a hasta."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        payload = build_calidad_territorio_payload(
            desde,
            hasta,
            filtros,
            limite_ejemplos=limite_ejemplos,
        )
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudo calcular calidad territorial (PostGIS F2 requerido).",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(payload)


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_catalogos_view(request):
    from django.db import connection

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, codigo, nombre
                FROM comuna
                WHERE COALESCE(activo, TRUE)
                ORDER BY nombre
                """
            )
            comunas = [
                {"id": r[0], "codigo": r[1], "nombre": r[2]} for r in cursor.fetchall()
            ]
            cursor.execute(
                """
                SELECT id, codigo, nombre
                FROM clase_incidente
                WHERE COALESCE(activo, TRUE)
                ORDER BY nombre
                """
            )
            clases = [{"id": r[0], "codigo": r[1], "nombre": r[2]} for r in cursor.fetchall()]
    except DatabaseError:
        return Response(
            {"detail": "No se pudieron cargar catálogos.", "comunas": [], "clases_incidente": []},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    return Response({"comunas": comunas, "clases_incidente": clases})


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_barrios_view(request):
    from django.db import connection

    raw = request.GET.get("comuna_id")
    if not raw:
        return Response({"barrios": []})

    try:
        comuna_id = int(raw)
    except ValueError:
        return Response(
            {"detail": "comuna_id inválido."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, codigo, nombre
                FROM barrio
                WHERE comuna_id = %s AND COALESCE(activo, TRUE)
                ORDER BY nombre
                """,
                [comuna_id],
            )
            barrios = [
                {"id": r[0], "codigo": r[1], "nombre": r[2]} for r in cursor.fetchall()
            ]
    except DatabaseError:
        return Response({"detail": "No se pudieron cargar barrios.", "barrios": []}, status=503)

    return Response({"barrios": barrios})


@api_view(["GET"])
@permission_classes([AllowAny])
def dashboard_comunas_geojson_view(request):
    """
    F3.7 — Límites comunales como GeoJSON (comuna.geom, EPSG:4326).

    Query opcional: comuna_id (solo una comuna).
    """
    comuna_id = _optional_int(request.GET, "comuna_id")
    try:
        payload = build_comunas_geojson(comuna_id)
    except DatabaseError as exc:
        payload = {
            "detail": "No se pudieron leer polígonos de comuna (PostGIS / comuna.geom).",
            "code": "db_error",
        }
        if settings.DEBUG:
            payload["debug"] = str(exc)
        return Response(payload, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response(payload)
