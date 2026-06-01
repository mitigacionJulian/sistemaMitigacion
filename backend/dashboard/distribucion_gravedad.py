"""
Distribución por gravedad comparativa: periodo actual vs mismo intervalo año anterior.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from django.db import connection

from .kpis import FiltrosKpi, _shift_year_back, _fatal_sql_expr
from .territorio_sql import append_filtros_territoriales, meta_filtros_dict, nota_modo_territorio


def _key_sql(alias_gv: str = "gv") -> str:
    g = alias_gv
    fatal = _fatal_sql_expr(g)
    return f"""CASE
      WHEN {fatal} THEN 'FATAL'
      WHEN lower({g}.nombre) LIKE '%%%%grave%%%%' OR upper({g}.codigo) LIKE '%%%%GRAVE%%%%' THEN 'GRAVE'
      WHEN lower({g}.nombre) LIKE '%%%%leve%%%%' OR upper({g}.codigo) LIKE '%%%%LEVE%%%%' THEN 'LEVE'
      ELSE 'OTRO'
    END"""


def _label_sql(alias_gv: str = "gv") -> str:
    g = alias_gv
    fatal = _fatal_sql_expr(g)
    return f"""CASE
      WHEN {fatal} THEN 'Fatal'
      WHEN lower({g}.nombre) LIKE '%%%%grave%%%%' OR upper({g}.codigo) LIKE '%%%%GRAVE%%%%' THEN 'Grave'
      WHEN lower({g}.nombre) LIKE '%%%%leve%%%%' OR upper({g}.codigo) LIKE '%%%%LEVE%%%%' THEN 'Leve'
      ELSE COALESCE(NULLIF(trim({g}.nombre), ''), 'Otro / sin clasificar')
    END"""


def _query_distribucion(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
) -> dict[str, tuple[str, int]]:
    where = ["i.fecha_incidente >= %s", "i.fecha_incidente <= %s"]
    params: list[Any] = [inicio, fin]
    append_filtros_territoriales(where, params, filtros)

    wh = " AND ".join(where)
    key_expr = _key_sql("gv")
    label_expr = _label_sql("gv")
    sql = f"""
    SELECT
      {key_expr} AS key,
      {label_expr} AS label,
      COUNT(v.id)::bigint AS total_victimas
    FROM incidente i
    LEFT JOIN victima v ON v.incidente_id = i.id
    LEFT JOIN gravedad_victima gv ON v.gravedad_victima_id = gv.id
    WHERE {wh}
    GROUP BY 1, 2
    ORDER BY 3 DESC
    """
    out: dict[str, tuple[str, int]] = {}
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        for row in cursor.fetchall():
            out[str(row[0])] = (str(row[1]), int(row[2] or 0))
    return out


def build_distribucion_gravedad_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    inicio_ant = _shift_year_back(inicio)
    fin_ant = _shift_year_back(fin)

    act = _query_distribucion(inicio, fin, filtros)
    ant = _query_distribucion(inicio_ant, fin_ant, filtros)

    order = ["FATAL", "GRAVE", "LEVE", "OTRO"]
    keys = list(dict.fromkeys(order + list(act.keys()) + list(ant.keys())))
    total_act = sum(v for _, v in act.values()) or 1
    total_ant = sum(v for _, v in ant.values()) or 1

    serie: list[dict[str, Any]] = []
    for k in keys:
        label = act.get(k, ant.get(k, ("Otro / sin clasificar", 0)))[0]
        v_act = act.get(k, (label, 0))[1]
        v_ant = ant.get(k, (label, 0))[1]
        serie.append(
            {
                "codigo": k,
                "gravedad": label,
                "victimas_periodo_actual": v_act,
                "victimas_periodo_anterior": v_ant,
                "porcentaje_actual": round(v_act * 100 / total_act, 2),
                "porcentaje_anterior": round(v_ant * 100 / total_ant, 2),
            }
        )

    return {
        "meta": {
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "fecha_inicio_anterior": inicio_ant.isoformat(),
            "fecha_fin_anterior": fin_ant.isoformat(),
            "filtros": meta_filtros_dict(filtros),
            "nota_territorio": nota_modo_territorio(filtros.modo_territorio),
        },
        "serie": serie,
    }
