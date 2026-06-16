"""
Reporte Tablero (Fase 1): agrega los mismos payloads que alimentan /tablero.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from dashboard.distribucion_clase_incidente import build_distribucion_clase_incidente_payload
from dashboard.distribucion_gravedad import build_distribucion_gravedad_payload
from dashboard.evolucion_mensual import build_evolucion_payload
from dashboard.kpis import FiltrosKpi, build_kpis_payload
from dashboard.matriz_dia_hora import build_matriz_dia_hora_payload
from dashboard.por_dia_semana import build_dia_semana_payload
from dashboard.tops import build_tops_payload

_DIA_CORTO = ("Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb")


def _resumen_matriz(serie: list[dict[str, Any]]) -> dict[str, Any]:
    """Totales por hora y top celdas día×hora para tablas compactas en impresión."""
    por_hora: list[dict[str, Any]] = []
    for h in range(24):
        actual = sum(c["total_incidentes_actual"] for c in serie if c["hora"] == h)
        anterior = sum(c["total_incidentes_anterior"] for c in serie if c["hora"] == h)
        por_hora.append(
            {
                "hora": h,
                "incidentes_actual": actual,
                "incidentes_anterior": anterior,
                "delta": actual - anterior,
            }
        )

    top_celdas = sorted(serie, key=lambda c: c["total_incidentes_actual"], reverse=True)[:12]
    for c in top_celdas:
        d = int(c["dia_semana"])
        c["dia_etiqueta"] = _DIA_CORTO[d] if 0 <= d < 7 else str(d)

    return {"por_hora": por_hora, "top_celdas": top_celdas}


def build_tablero_report_body(
    desde: date,
    hasta: date,
    filtros: FiltrosKpi,
    *,
    top_n: int = 10,
) -> dict[str, Any]:
    kpis = build_kpis_payload(desde, hasta, filtros)
    evolucion = build_evolucion_payload(desde, hasta, filtros)
    dia_semana = build_dia_semana_payload(desde, hasta, filtros)
    matriz = build_matriz_dia_hora_payload(desde, hasta, filtros)
    clase = build_distribucion_clase_incidente_payload(desde, hasta, filtros)
    gravedad = build_distribucion_gravedad_payload(desde, hasta, filtros)
    tops = build_tops_payload(desde, hasta, filtros, limite=top_n)

    matriz_resumen = _resumen_matriz(matriz.get("serie") or [])

    return {
        "tipo": "tablero",
        "kpis": kpis,
        "evolucion_mensual": evolucion,
        "dia_semana": dia_semana,
        "matriz_dia_hora": {
            "meta": matriz.get("meta"),
            "serie": matriz.get("serie"),
            "resumen": matriz_resumen,
        },
        "distribucion_clase_incidente": clase,
        "distribucion_gravedad": gravedad,
        "tops": tops,
    }
