"""Reporte Predicciones (Fase 3): proyección mensual, prioridad, carga y patrones."""

from __future__ import annotations

from datetime import date
from typing import Any

from dashboard.carga_esperada_territorial import build_carga_esperada_payload
from dashboard.kpis import FiltrosKpi
from dashboard.patrones_temporales_proyectados import (
    build_dia_semana_proyectado_payload,
    build_matriz_dia_hora_proyectada_payload,
)
from dashboard.predicciones_mensuales import build_predicciones_mensuales_payload
from dashboard.prioridad_territorial import build_prioridad_territorial_payload
from dashboard.proporcion_fatales_mensual import build_proporcion_fatales_payload

from .params import PrediccionesQuery

_DIA_CORTO = ("Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb")

AVISO_PROYECCIONES = (
    "Las cifras de proyección son estimaciones modeladas a partir del periodo histórico filtrado; "
    "no son hechos observados ni predicciones causales. Úselas como apoyo exploratorio para analistas."
)


def _select_serie_desglose(
    payload: dict[str, Any],
    *,
    desglose_key: str,
    series_key: str,
    idx: int,
) -> dict[str, Any]:
    meta = payload.get("meta") or {}
    if meta.get(desglose_key) and payload.get(series_key):
        series = payload[series_key]
        if not series:
            return payload
        pick = series[min(max(idx, 0), len(series) - 1)]
        return {
            "meta": pick.get("meta") or meta,
            "serie_historica": pick.get("serie_historica") or [],
            "proyeccion": pick.get("proyeccion") or [],
            "desglose": {
                desglose_key: True,
                "indice": min(max(idx, 0), len(series) - 1),
                "total_series": len(series),
                **{
                    k: pick.get(k)
                    for k in ("clase_incidente_id", "clase_nombre", "comuna_id", "comuna_nombre")
                    if pick.get(k) is not None
                },
            },
        }
    return {
        "meta": meta,
        "serie_historica": payload.get("serie_historica") or [],
        "proyeccion": payload.get("proyeccion") or [],
        "desglose": {desglose_key: False},
    }


def _tabla_mensual(serie_historica: list[dict], proyeccion: list[dict]) -> list[dict[str, Any]]:
    filas: list[dict[str, Any]] = []
    for r in serie_historica:
        filas.append(
            {
                "mes": r.get("mes_etiqueta") or r.get("mes_clave"),
                "tipo": "observado",
                "valor": r.get("observados") if r.get("observados") is not None else r.get("incidentes_observados"),
                "ajuste": r.get("ajuste_modelo") if r.get("ajuste_modelo") is not None else r.get("incidentes_ajuste_lineal"),
            }
        )
    for r in proyeccion:
        filas.append(
            {
                "mes": r.get("mes_etiqueta") or r.get("mes_clave"),
                "tipo": "proyectado",
                "valor": r.get("proyectados") if r.get("proyectados") is not None else r.get("incidentes_proyectados"),
                "ajuste": r.get("ajuste_modelo") if r.get("ajuste_modelo") is not None else r.get("incidentes_ajuste_lineal"),
            }
        )
    return filas


def _tabla_proporcion(serie_historica: list[dict], proyeccion: list[dict]) -> list[dict[str, Any]]:
    filas: list[dict[str, Any]] = []
    for r in serie_historica:
        filas.append(
            {
                "mes": r.get("mes_etiqueta") or r.get("mes_clave"),
                "tipo": "observado",
                "pct_fatales": r.get("pct_fatales"),
                "ajuste": r.get("ajuste_pct"),
            }
        )
    for r in proyeccion:
        filas.append(
            {
                "mes": r.get("mes_etiqueta") or r.get("mes_clave"),
                "tipo": "proyectado",
                "pct_fatales": None,
                "ajuste": r.get("pct_fatales_proyectado") if r.get("pct_fatales_proyectado") is not None else r.get("ajuste_pct"),
            }
        )
    return filas


def _resumen_matriz_proyectada(serie: list[dict[str, Any]]) -> dict[str, Any]:
    por_hora: list[dict[str, Any]] = []
    for h in range(24):
        obs = sum(c.get("incidentes_observados_periodo") or 0 for c in serie if c.get("hora") == h)
        pr = sum(c.get("incidentes_proyectados_horizonte") or 0 for c in serie if c.get("hora") == h)
        por_hora.append(
            {
                "hora": h,
                "incidentes_observados": obs,
                "incidentes_proyectados": pr,
                "delta": pr - obs,
            }
        )

    top_celdas = sorted(
        serie,
        key=lambda c: c.get("incidentes_proyectados_horizonte") or 0,
        reverse=True,
    )[:12]
    for c in top_celdas:
        d = int(c.get("dia_semana", -1))
        c["dia_etiqueta"] = _DIA_CORTO[d] if 0 <= d < 7 else str(d)

    return {"por_hora": por_hora, "top_celdas": top_celdas}


def build_predicciones_report_body(
    desde: date,
    hasta: date,
    filtros: FiltrosKpi,
    pred_query: PrediccionesQuery,
) -> dict[str, Any]:
    pred_raw = build_predicciones_mensuales_payload(
        desde,
        hasta,
        filtros,
        pred_query.horizonte_meses,
        modelo=pred_query.modelo_pred,
        variable=pred_query.variable,
        desglose_clase=pred_query.desglose_clase,
        excluir_covid=pred_query.excluir_covid,
        ventana_ma=pred_query.ventana_ma,
    )
    predicciones = _select_serie_desglose(
        pred_raw,
        desglose_key="desglose_clase",
        series_key="series_por_clase",
        idx=pred_query.serie_clase_idx,
    )
    predicciones["tabla_mensual"] = _tabla_mensual(
        predicciones.get("serie_historica") or [],
        predicciones.get("proyeccion") or [],
    )

    prioridad = build_prioridad_territorial_payload(
        desde,
        hasta,
        filtros,
        nivel=pred_query.nivel_prioridad,
        limite=pred_query.limite_prioridad,
        excluir_covid=pred_query.excluir_covid,
    )

    prop_raw = build_proporcion_fatales_payload(
        desde,
        hasta,
        filtros,
        horizonte_meses=pred_query.horizonte_meses,
        modelo=pred_query.modelo_prop,
        excluir_covid=pred_query.excluir_covid,
        desglose_comuna=pred_query.desglose_comuna,
        ventana_ma=pred_query.ventana_ma,
    )
    proporcion = _select_serie_desglose(
        prop_raw,
        desglose_key="desglose_comuna",
        series_key="series_por_comuna",
        idx=pred_query.serie_comuna_idx,
    )
    proporcion["tabla_mensual"] = _tabla_proporcion(
        proporcion.get("serie_historica") or [],
        proporcion.get("proyeccion") or [],
    )

    carga = build_carga_esperada_payload(
        desde,
        hasta,
        filtros,
        nivel=pred_query.nivel_carga,
        horizonte_meses=pred_query.horizonte_meses,
        modelo=pred_query.modelo_carga,
        excluir_covid=pred_query.excluir_covid,
        limite=pred_query.limite_carga,
        ventana_ma=pred_query.ventana_ma,
    )

    matriz = build_matriz_dia_hora_proyectada_payload(
        desde,
        hasta,
        filtros,
        horizonte_meses=pred_query.horizonte_meses,
        modelo=pred_query.modelo_carga,
        excluir_covid=pred_query.excluir_covid,
        ventana_ma=pred_query.ventana_ma,
    )
    matriz_serie = matriz.get("serie") or []
    matriz = {
        **matriz,
        "resumen": _resumen_matriz_proyectada(matriz_serie),
    }

    dia_semana = build_dia_semana_proyectado_payload(
        desde,
        hasta,
        filtros,
        horizonte_meses=pred_query.horizonte_meses,
        modelo=pred_query.modelo_carga,
        excluir_covid=pred_query.excluir_covid,
        ventana_ma=pred_query.ventana_ma,
    )

    return {
        "tipo": "predicciones",
        "aviso": AVISO_PROYECCIONES,
        "configuracion": {
            "horizonte_meses": pred_query.horizonte_meses,
            "modelo_pred": pred_query.modelo_pred,
            "modelo_prop": pred_query.modelo_prop,
            "modelo_carga": pred_query.modelo_carga,
            "variable": pred_query.variable,
            "ventana_ma": pred_query.ventana_ma,
            "nivel_prioridad": pred_query.nivel_prioridad,
            "nivel_carga": pred_query.nivel_carga,
            "excluir_covid": pred_query.excluir_covid,
            "desglose_clase": pred_query.desglose_clase,
            "desglose_comuna": pred_query.desglose_comuna,
        },
        "predicciones_mensuales": predicciones,
        "prioridad_territorial": prioridad,
        "proporcion_fatales": proporcion,
        "carga_esperada": carga,
        "matriz_dia_hora_proyectada": matriz,
        "dia_semana_proyectado": dia_semana,
    }
