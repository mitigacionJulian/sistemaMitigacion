"""
Evolución mensual en el rango [desde, hasta], con comparación al mismo intervalo un año antes.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from django.db import connection

from .kpis import FiltrosKpi, _shift_year_back
from .territorio_sql import append_filtros_territoriales, meta_filtros_dict, nota_modo_territorio

_MESES_CORTO = (
    "ene",
    "feb",
    "mar",
    "abr",
    "may",
    "jun",
    "jul",
    "ago",
    "sep",
    "oct",
    "nov",
    "dic",
)


def _iter_meses_clave(inicio: date, fin: date) -> list[str]:
    """Claves 'YYYY-MM' para cada mes calendario que intersecta [inicio, fin]."""
    out: list[str] = []
    y, m = inicio.year, inicio.month
    fin_y, fin_m = fin.year, fin.month
    while (y, m) <= (fin_y, fin_m):
        out.append(f"{y:04d}-{m:02d}")
        if m == 12:
            y, m = y + 1, 1
        else:
            m += 1
    return out


def _etiqueta_mes_ym(ym: str) -> str:
    y, mm = ym.split("-")
    return f"{_MESES_CORTO[int(mm) - 1]} {y}"


def _ym_menos_un_anio(ym: str) -> str:
    """Pasa 'YYYY-MM' al mismo mes del año anterior (coherente con KPIs)."""
    y, mo = map(int, ym.split("-"))
    d1 = date(y, mo, 1)
    d0 = _shift_year_back(d1)
    return f"{d0.year:04d}-{d0.month:02d}"


def _query_agregado_por_mes(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
) -> dict[str, tuple[int, int]]:
    filtros = filtros or FiltrosKpi()

    where = ["i.fecha_incidente >= %s", "i.fecha_incidente <= %s"]
    params: list[Any] = [inicio, fin]

    append_filtros_territoriales(where, params, filtros)

    wh = " AND ".join(where)

    sql = f"""
    SELECT
      to_char(i.fecha_incidente, 'YYYY-MM') AS mes,
      COUNT(DISTINCT i.id)::bigint AS total_incidentes,
      COUNT(v.id)::bigint AS total_victimas
    FROM incidente i
    LEFT JOIN victima v ON v.incidente_id = i.id
    WHERE {wh}
    GROUP BY to_char(i.fecha_incidente, 'YYYY-MM')
    ORDER BY mes
    """

    out: dict[str, tuple[int, int]] = {}
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        for row in cursor.fetchall():
            mes = row[0]
            out[mes] = (int(row[1] or 0), int(row[2] or 0))
    return out


def build_evolucion_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()

    inicio_ant = _shift_year_back(inicio)
    fin_ant = _shift_year_back(fin)

    act = _query_agregado_por_mes(inicio, fin, filtros)
    ant = _query_agregado_por_mes(inicio_ant, fin_ant, filtros)

    meses = _iter_meses_clave(inicio, fin)
    serie: list[dict[str, Any]] = []
    for mk in meses:
        mk_ant = _ym_menos_un_anio(mk)
        ia, va = act.get(mk, (0, 0))
        ib, vb = ant.get(mk_ant, (0, 0))
        serie.append(
            {
                "mes_clave": mk,
                "mes_etiqueta": _etiqueta_mes_ym(mk),
                "incidentes_periodo_actual": ia,
                "victimas_periodo_actual": va,
                "incidentes_periodo_anterior": ib,
                "victimas_periodo_anterior": vb,
            }
        )

    return {
        "meta": {
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "fecha_inicio_anterior": inicio_ant.isoformat(),
            "fecha_fin_anterior": fin_ant.isoformat(),
            "descripcion": (
                "Totales por mes natural dentro del rango seleccionado; la columna comparada usa el mismo mes "
                "en el intervalo equivalente del año anterior (alineado con los KPIs)."
            ),
            "filtros": meta_filtros_dict(filtros),
            "nota_territorio": nota_modo_territorio(filtros.modo_territorio),
        },
        "serie": serie,
    }
