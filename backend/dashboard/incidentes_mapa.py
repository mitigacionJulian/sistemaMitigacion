"""
Puntos de incidentes con coordenadas válidas para mapas (muestra acotada).

Sirve para visualizar concentración geográfica; no sustituye análisis espacial
estadístico ni densidad kernel formal.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from django.db import connection

from .kpis import FiltrosKpi

# Si el cliente envía limite=0 (“sin límite práctico”), no se omite LIMIT en SQL:
# se usa min(total_en_rango, este tope) para proteger BD y navegador.
MAPA_CAP_SIN_LIMITE = 100_000


def _query_incidentes_puntos(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
    limite_filas: int | None,
    cap_sin_limite: int = MAPA_CAP_SIN_LIMITE,
) -> tuple[list[dict[str, Any]], int]:
    """
    Devuelve (puntos, total_en_rango_sin_limite_aprox).
    total: cuenta con el mismo WHERE sin LIMIT (puede ser costoso; se usa solo meta).

    Si ``limite_filas`` es None (modo “sin límite” solicitado por API), el LIMIT del SELECT
    es ``min(total, cap_sin_limite)``.
    """
    where = [
        "i.fecha_incidente >= %s",
        "i.fecha_incidente <= %s",
        "i.latitud IS NOT NULL",
        "i.longitud IS NOT NULL",
        "CAST(i.latitud AS DOUBLE PRECISION) BETWEEN 1 AND 11",
        "CAST(i.longitud AS DOUBLE PRECISION) BETWEEN -79 AND -74",
    ]
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

    sql_count = f"SELECT COUNT(*)::bigint FROM incidente i WHERE {wh}"
    sql_points = f"""
    SELECT
      i.id,
      i.radicado,
      i.fecha_incidente,
      CAST(i.latitud AS DOUBLE PRECISION) AS latitud,
      CAST(i.longitud AS DOUBLE PRECISION) AS longitud,
      ci.nombre AS clase_incidente
    FROM incidente i
    LEFT JOIN clase_incidente ci ON ci.id = i.clase_incidente_id
    WHERE {wh}
    ORDER BY i.fecha_incidente DESC, i.id DESC
    LIMIT %s
    """
    puntos: list[dict[str, Any]] = []
    total = 0
    with connection.cursor() as cursor:
        cursor.execute(sql_count, params)
        row = cursor.fetchone()
        total = int(row[0] or 0) if row else 0

        if limite_filas is None:
            sql_limit = min(total, cap_sin_limite) if total > 0 else 0
        else:
            sql_limit = limite_filas

        params_lim = list(params) + [sql_limit]
        cursor.execute(sql_points, params_lim)
        for row in cursor.fetchall():
            puntos.append(
                {
                    "id": int(row[0]),
                    "radicado": row[1],
                    "fecha_incidente": row[2].isoformat() if row[2] else None,
                    "latitud": float(row[3]),
                    "longitud": float(row[4]),
                    "clase_incidente": row[5] or "",
                }
            )
    return puntos, total


def build_incidentes_mapa_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
    limite: int = 10_000,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    sin_limite_solicitado = int(limite) == 0
    if sin_limite_solicitado:
        puntos, total_con_coord = _query_incidentes_puntos(
            inicio, fin, filtros, None, MAPA_CAP_SIN_LIMITE
        )
        lim_aplicado = min(total_con_coord, MAPA_CAP_SIN_LIMITE) if total_con_coord > 0 else 0
    else:
        lim = max(100, min(MAPA_CAP_SIN_LIMITE, int(limite)))
        puntos, total_con_coord = _query_incidentes_puntos(inicio, fin, filtros, lim)
        lim_aplicado = lim

    truncado = total_con_coord > len(puntos)
    recorte_abs = sin_limite_solicitado and total_con_coord > MAPA_CAP_SIN_LIMITE
    return {
        "meta": {
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "limite": lim_aplicado,
            "sin_limite_solicitado": sin_limite_solicitado,
            "tope_absoluto_sin_limite": MAPA_CAP_SIN_LIMITE if sin_limite_solicitado else None,
            "recorte_por_tope_absoluto": recorte_abs,
            "total_con_coordenadas_en_rango": total_con_coord,
            "puntos_devueltos": len(puntos),
            "muestra_truncada": truncado,
            "descripcion": (
                "Incidentes con latitud y longitud no nulas en el rango; orden descendente por fecha. "
                "La capa usa círculos semitransparentes: donde hay más solapamiento se percibe mayor densidad."
            ),
            "filtros": {
                "comuna_id": filtros.comuna_id,
                "barrio_id": filtros.barrio_id,
                "clase_incidente_id": filtros.clase_incidente_id,
            },
        },
        "puntos": puntos,
    }
