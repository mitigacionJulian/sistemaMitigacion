"""
Rankings (tops) por sexo, edad, condición, comuna y barrio en el periodo filtrado.
Conteos sobre víctimas ligadas a incidentes en el rango de fechas.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from django.db import connection

from .kpis import FiltrosKpi
from .territorio_sql import (
    append_filtros_territoriales,
    comuna_fk_col,
    barrio_fk_col,
    meta_filtros_dict,
    nota_modo_territorio,
)


def _where_sql(filtros: FiltrosKpi) -> tuple[str, list[Any]]:
    where = ["i.fecha_incidente >= %s", "i.fecha_incidente <= %s"]
    params: list[Any] = []
    append_filtros_territoriales(where, params, filtros)
    return " AND ".join(where), params


def _total_victimas(inicio: date, fin: date, filtros: FiltrosKpi) -> int:
    wh, base_params = _where_sql(filtros)
    params = [inicio, fin] + base_params
    sql = f"""
    SELECT COUNT(v.id)::bigint
    FROM victima v
    INNER JOIN incidente i ON v.incidente_id = i.id
    WHERE {wh}
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def _pct(n: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(n * 100 / total, 2)


def build_tops_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
    limite: int = 10,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    limite = min(max(int(limite), 1), 25)

    wh, base_params = _where_sql(filtros)
    params_base = [inicio, fin] + base_params
    total_v = _total_victimas(inicio, fin, filtros)
    c_fk = comuna_fk_col(filtros.modo_territorio)
    b_fk = barrio_fk_col(filtros.modo_territorio)

    def rows_sexo() -> list[dict[str, Any]]:
        sql = f"""
        SELECT s.id, COALESCE(s.codigo, '') AS codigo,
               COALESCE(NULLIF(trim(s.nombre), ''), 'Sin especificar') AS nombre,
               COUNT(v.id)::bigint AS total
        FROM victima v
        INNER JOIN incidente i ON v.incidente_id = i.id
        LEFT JOIN sexo s ON v.sexo_id = s.id
        WHERE {wh}
        GROUP BY s.id, s.codigo, s.nombre
        ORDER BY total DESC
        LIMIT %s
        """
        out: list[dict[str, Any]] = []
        with connection.cursor() as cursor:
            cursor.execute(sql, params_base + [limite])
            for row in cursor.fetchall():
                t = int(row[3] or 0)
                out.append(
                    {
                        "sexo_id": row[0],
                        "codigo": str(row[1] or ""),
                        "nombre": str(row[2] or ""),
                        "total_victimas": t,
                        "porcentaje": _pct(t, total_v),
                    }
                )
        return out

    def rows_edad() -> list[dict[str, Any]]:
        sql = f"""
        SELECT v.edad, COUNT(v.id)::bigint AS total
        FROM victima v
        INNER JOIN incidente i ON v.incidente_id = i.id
        WHERE {wh}
        GROUP BY v.edad
        ORDER BY total DESC
        LIMIT %s
        """
        out: list[dict[str, Any]] = []
        with connection.cursor() as cursor:
            cursor.execute(sql, params_base + [limite])
            for row in cursor.fetchall():
                edad_val = row[0]
                t = int(row[1] or 0)
                if edad_val is None:
                    etiqueta = "Sin edad"
                else:
                    etiqueta = f"{int(edad_val)} años"
                out.append(
                    {
                        "edad": edad_val,
                        "etiqueta": etiqueta,
                        "total_victimas": t,
                        "porcentaje": _pct(t, total_v),
                    }
                )
        return out

    def rows_condicion() -> list[dict[str, Any]]:
        sql = f"""
        SELECT c.id, COALESCE(c.codigo, '') AS codigo,
               COALESCE(NULLIF(trim(c.nombre), ''), 'Sin especificar') AS nombre,
               COUNT(v.id)::bigint AS total
        FROM victima v
        INNER JOIN incidente i ON v.incidente_id = i.id
        LEFT JOIN condicion c ON v.condicion_id = c.id
        WHERE {wh}
        GROUP BY c.id, c.codigo, c.nombre
        ORDER BY total DESC
        LIMIT %s
        """
        out: list[dict[str, Any]] = []
        with connection.cursor() as cursor:
            cursor.execute(sql, params_base + [limite])
            for row in cursor.fetchall():
                t = int(row[3] or 0)
                out.append(
                    {
                        "condicion_id": row[0],
                        "codigo": str(row[1] or ""),
                        "nombre": str(row[2] or ""),
                        "total_victimas": t,
                        "porcentaje": _pct(t, total_v),
                    }
                )
        return out

    def rows_comuna() -> list[dict[str, Any]]:
        sql = f"""
        SELECT co.id, COALESCE(co.codigo, '') AS codigo,
               COALESCE(NULLIF(trim(co.nombre), ''), 'Sin especificar') AS nombre,
               COUNT(v.id)::bigint AS total
        FROM victima v
        INNER JOIN incidente i ON v.incidente_id = i.id
        LEFT JOIN comuna co ON i.{c_fk} = co.id
        WHERE {wh}
        GROUP BY co.id, co.codigo, co.nombre
        ORDER BY total DESC
        LIMIT %s
        """
        out: list[dict[str, Any]] = []
        with connection.cursor() as cursor:
            cursor.execute(sql, params_base + [limite])
            for row in cursor.fetchall():
                t = int(row[3] or 0)
                out.append(
                    {
                        "comuna_id": row[0],
                        "codigo": str(row[1] or ""),
                        "nombre": str(row[2] or ""),
                        "total_victimas": t,
                        "porcentaje": _pct(t, total_v),
                    }
                )
        return out

    def rows_barrio() -> list[dict[str, Any]]:
        sql = f"""
        SELECT b.id, COALESCE(b.codigo, '') AS codigo,
               COALESCE(NULLIF(trim(b.nombre), ''), 'Sin especificar') AS nombre,
               COALESCE(NULLIF(trim(co.nombre), ''), '') AS comuna_nombre,
               COUNT(v.id)::bigint AS total
        FROM victima v
        INNER JOIN incidente i ON v.incidente_id = i.id
        LEFT JOIN barrio b ON i.{b_fk} = b.id
        LEFT JOIN comuna co ON b.comuna_id = co.id
        WHERE {wh}
        GROUP BY b.id, b.codigo, b.nombre, co.nombre
        ORDER BY total DESC
        LIMIT %s
        """
        out: list[dict[str, Any]] = []
        with connection.cursor() as cursor:
            cursor.execute(sql, params_base + [limite])
            for row in cursor.fetchall():
                t = int(row[4] or 0)
                comuna_nom = str(row[3] or "").strip()
                nombre_bar = str(row[2] or "")
                out.append(
                    {
                        "barrio_id": row[0],
                        "codigo": str(row[1] or ""),
                        "nombre": nombre_bar,
                        "comuna_nombre": comuna_nom,
                        "total_victimas": t,
                        "porcentaje": _pct(t, total_v),
                    }
                )
        return out

    sexo = rows_sexo()
    edad = rows_edad()
    condicion = rows_condicion()
    comuna = rows_comuna()
    barrio = rows_barrio()

    def rank(rows: list[dict[str, Any]]) -> None:
        for i, row in enumerate(rows, start=1):
            row["rank"] = i

    rank(sexo)
    rank(edad)
    rank(condicion)
    rank(comuna)
    rank(barrio)

    return {
        "meta": {
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "total_victimas_periodo": total_v,
            "limite": limite,
            "filtros": meta_filtros_dict(filtros),
            "nota_territorio": nota_modo_territorio(filtros.modo_territorio),
            "nota": (
                "Porcentajes respecto al total de víctimas en el periodo con los mismos filtros. "
                "Una sola respuesta agrupa varios rankings; en pantalla suelen mostrarse como tablas separadas "
                "por legibilidad."
            ),
        },
        "sexo": sexo,
        "edad": edad,
        "condicion": condicion,
        "comuna": comuna,
        "barrio": barrio,
    }
