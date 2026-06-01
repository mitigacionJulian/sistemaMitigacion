"""
Matriz día/hora comparativa: periodo actual vs mismo intervalo del año anterior.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from django.db import connection

from .kpis import FiltrosKpi, _shift_year_back
from .territorio_sql import append_filtros_territoriales, meta_filtros_dict, nota_modo_territorio


def _query_heatmap(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
) -> dict[tuple[int, int], int]:
    where = ["i.fecha_incidente >= %s", "i.fecha_incidente <= %s"]
    params: list[Any] = [inicio, fin]

    append_filtros_territoriales(where, params, filtros)

    wh = " AND ".join(where)
    sql = f"""
    SELECT
      EXTRACT(DOW FROM i.fecha_incidente)::int AS dia_semana,
      EXTRACT(HOUR FROM i.hora_incidente)::int AS hora,
      COUNT(DISTINCT i.id)::bigint AS total_incidentes
    FROM incidente i
    WHERE {wh}
    GROUP BY 1, 2
    ORDER BY 1, 2
    """

    out: dict[tuple[int, int], int] = {}
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        for row in cursor.fetchall():
            out[(int(row[0]), int(row[1]))] = int(row[2] or 0)
    return out


def build_matriz_dia_hora_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    inicio_ant = _shift_year_back(inicio)
    fin_ant = _shift_year_back(fin)

    actual = _query_heatmap(inicio, fin, filtros)
    anterior = _query_heatmap(inicio_ant, fin_ant, filtros)

    serie: list[dict[str, Any]] = []
    max_actual = 0
    for d in range(7):
        for h in range(24):
            a = actual.get((d, h), 0)
            b = anterior.get((d, h), 0)
            max_actual = max(max_actual, a)
            serie.append(
                {
                    "dia_semana": d,
                    "hora": h,
                    "total_incidentes_actual": a,
                    "total_incidentes_anterior": b,
                    "delta_abs": a - b,
                }
            )

    return {
        "meta": {
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "fecha_inicio_anterior": inicio_ant.isoformat(),
            "fecha_fin_anterior": fin_ant.isoformat(),
            "max_actual": max_actual,
            "filtros": meta_filtros_dict(filtros),
            "nota_territorio": nota_modo_territorio(filtros.modo_territorio),
        },
        "serie": serie,
    }
