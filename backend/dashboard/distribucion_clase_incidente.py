"""
Distribución de incidentes por clase de incidente: periodo actual vs mismo intervalo del año anterior.
Cuenta filas en `incidente` (no víctimas).
"""
from __future__ import annotations

from datetime import date
from typing import Any

from django.db import connection

from .kpis import FiltrosKpi, _shift_year_back


def _query_por_clase(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
) -> dict[int | None, tuple[str, str, int]]:
    where = ["i.fecha_incidente >= %s", "i.fecha_incidente <= %s"]
    params: list[Any] = [inicio, fin]
    if filtros.comuna_id is not None:
        where.append("i.comuna_id = %s")
        params.append(filtros.comuna_id)
    if filtros.barrio_id is not None:
        where.append("i.barrio_id = %s")
        params.append(filtros.barrio_id)
    if filtros.clase_incidente_id is not None:
        where.append("i.clase_incidente_id = %s")
        params.append(filtros.clase_incidente_id)

    wh = " AND ".join(where)
    sql = f"""
    SELECT
      i.clase_incidente_id,
      COALESCE(ci.codigo, '') AS codigo,
      COALESCE(NULLIF(trim(ci.nombre), ''), 'Sin clasificar') AS nombre,
      COUNT(i.id)::bigint AS total_incidentes
    FROM incidente i
    LEFT JOIN clase_incidente ci ON i.clase_incidente_id = ci.id
    WHERE {wh}
    GROUP BY i.clase_incidente_id, ci.codigo, ci.nombre
    """
    out: dict[int | None, tuple[str, str, int]] = {}
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        for row in cursor.fetchall():
            cid = row[0]
            codigo = str(row[1] or "")
            nombre = str(row[2] or "Sin clasificar")
            total = int(row[3] or 0)
            out[cid] = (codigo, nombre, total)
    return out


def build_distribucion_clase_incidente_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    inicio_ant = _shift_year_back(inicio)
    fin_ant = _shift_year_back(fin)

    act = _query_por_clase(inicio, fin, filtros)
    ant = _query_por_clase(inicio_ant, fin_ant, filtros)

    keys = list(dict.fromkeys(list(act.keys()) + list(ant.keys())))
    total_act = sum(v[2] for v in act.values()) or 1
    total_ant = sum(v[2] for v in ant.values()) or 1

    serie: list[dict[str, Any]] = []
    for cid in keys:
        cod_a, nom_a, n_act = act.get(cid, ("", "Sin clasificar", 0))
        cod_b, nom_b, n_ant = ant.get(cid, ("", nom_a, 0))
        nombre = nom_a if n_act or cid in act else nom_b
        codigo = cod_a or cod_b
        serie.append(
            {
                "clase_incidente_id": cid,
                "codigo": codigo,
                "clase": nombre,
                "incidentes_periodo_actual": n_act,
                "incidentes_periodo_anterior": n_ant,
                "porcentaje_actual": round(n_act * 100 / total_act, 2),
                "porcentaje_anterior": round(n_ant * 100 / total_ant, 2),
            }
        )

    serie.sort(
        key=lambda x: (-x["incidentes_periodo_actual"], str(x["clase"]).lower()),
    )

    return {
        "meta": {
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "fecha_inicio_anterior": inicio_ant.isoformat(),
            "fecha_fin_anterior": fin_ant.isoformat(),
            "filtros": {
                "comuna_id": filtros.comuna_id,
                "barrio_id": filtros.barrio_id,
                "clase_incidente_id": filtros.clase_incidente_id,
            },
            "descripcion": (
                "Conteo de incidentes por clase según `incidente.clase_incidente_id`; "
                "comparación con el mismo intervalo del año anterior."
            ),
        },
        "serie": serie,
    }
