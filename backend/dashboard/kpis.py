"""
Agregados de KPIs sobre tablas `incidente` / `victima` / `gravedad_victima` (PostgreSQL).
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from typing import Any

from django.db import connection

from .territorio_sql import append_filtros_territoriales, meta_filtros_dict, nota_modo_territorio


def _shift_year_back(d: date) -> date:
    """Misma fecha calendario un año atrás (ajusta 29 feb)."""
    y = d.year - 1
    m, day = d.month, d.day
    last = calendar.monthrange(y, m)[1]
    return date(y, m, min(day, last))


def dias_en_rango(inicio: date, fin: date) -> int:
    return (fin - inicio).days + 1


def variacion_porcentual(actual: int, anterior: int) -> float | None:
    if anterior == 0:
        return None
    return round((actual - anterior) / anterior * 100, 2)


def variacion_porcentual_float(actual: float, anterior: float) -> float | None:
    if anterior == 0:
        return None
    return round((actual - anterior) / anterior * 100, 2)


@dataclass(frozen=True)
class FiltrosKpi:
    comuna_id: int | None = None
    barrio_id: int | None = None
    clase_incidente_id: int | None = None
    via_id: int | None = None
    punto_critico_id: int | None = None
    modo_territorio: str = "registro"
    punto_critico_modo: str = "registro"


def _fatal_sql_expr(alias_gv: str = "gv") -> str:
    """Condición SQL para víctima fatal según catálogo normalizado o texto."""
    g = alias_gv
    # psycopg2: '%' literal en el SQL como '%%'; dentro de f-string usar '%%%%' para obtener '%%' en el SQL enviado.
    return f"""(
      {g}.codigo IS NOT NULL AND (
        upper({g}.codigo) = 'FATAL'
        OR upper({g}.codigo) LIKE '%%%%FATAL%%%%'
        OR lower({g}.nombre) LIKE '%%%%fatal%%%%'
        OR lower({g}.nombre) LIKE '%%%%muert%%%%'
        OR lower({g}.nombre) LIKE '%%%%fallec%%%%'
      )
    )"""


def aggregate_period(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
) -> dict[str, Any]:
    """
    Devuelve totales en el rango [inicio, fin] (inclusive por fecha de incidente).
    """
    filtros = filtros or FiltrosKpi()
    fatal = _fatal_sql_expr("gv")

    where = ["i.fecha_incidente >= %s", "i.fecha_incidente <= %s"]
    params: list[Any] = [inicio, fin]

    append_filtros_territoriales(where, params, filtros)

    wh = " AND ".join(where)

    sql = f"""
    SELECT
      COUNT(DISTINCT i.id)::bigint AS total_incidentes,
      COUNT(v.id)::bigint AS total_victimas,
      COALESCE(SUM(CASE WHEN {fatal} THEN 1 ELSE 0 END), 0)::bigint AS victimas_fatales
    FROM incidente i
    LEFT JOIN victima v ON v.incidente_id = i.id
    LEFT JOIN gravedad_victima gv ON v.gravedad_victima_id = gv.id
    WHERE {wh}
    """

    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()

    if not row:
        tot_i, tot_v, fat = 0, 0, 0
    else:
        tot_i, tot_v, fat = (int(row[0] or 0), int(row[1] or 0), int(row[2] or 0))

    dias = max(1, dias_en_rango(inicio, fin))
    tasa = round(tot_i / dias, 4)

    return {
        "total_incidentes": tot_i,
        "total_victimas": tot_v,
        "victimas_fatales": fat,
        "tasa_incidentes_por_dia": tasa,
        "dias_en_periodo": dias,
    }


def build_kpis_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()

    inicio_ant = _shift_year_back(inicio)
    fin_ant = _shift_year_back(fin)

    actual = aggregate_period(inicio, fin, filtros)
    anterior = aggregate_period(inicio_ant, fin_ant, filtros)

    def cmp(key: str):
        a, p = actual[key], anterior[key]
        if key == "dias_en_periodo":
            return None
        if key == "tasa_incidentes_por_dia":
            return variacion_porcentual_float(
                float(actual["tasa_incidentes_por_dia"]),
                float(anterior["tasa_incidentes_por_dia"]),
            )
        return variacion_porcentual(int(a), int(p))

    comparacion = {
        "total_incidentes": {
            "variacion_pct": cmp("total_incidentes"),
            "valor_anterior": anterior["total_incidentes"],
            "valor_actual": actual["total_incidentes"],
        },
        "total_victimas": {
            "variacion_pct": cmp("total_victimas"),
            "valor_anterior": anterior["total_victimas"],
            "valor_actual": actual["total_victimas"],
        },
        "victimas_fatales": {
            "variacion_pct": cmp("victimas_fatales"),
            "valor_anterior": anterior["victimas_fatales"],
            "valor_actual": actual["victimas_fatales"],
        },
        "tasa_incidentes_por_dia": {
            "variacion_pct": cmp("tasa_incidentes_por_dia"),
            "valor_anterior": anterior["tasa_incidentes_por_dia"],
            "valor_actual": actual["tasa_incidentes_por_dia"],
        },
    }

    return {
        "meta": {
            "es_demostracion": False,
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "fecha_inicio_anterior": inicio_ant.isoformat(),
            "fecha_fin_anterior": fin_ant.isoformat(),
            "filtros": meta_filtros_dict(filtros),
            "nota_territorio": nota_modo_territorio(filtros.modo_territorio),
        },
        "kpis_periodo_actual": actual,
        "kpis_periodo_anterior": anterior,
        "comparacion": comparacion,
    }
