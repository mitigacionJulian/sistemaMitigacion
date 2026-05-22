"""
Fase C — P09/P10 series mensuales por comuna/barrio; P11 ranking por vía o punto crítico.

P09/P10: proyección mes a mes por territorio (comparar con mapa / tops).
P11: top vías o puntos críticos con carga proyectada en el horizonte.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Literal

from django.db import connection

from .kpis import FiltrosKpi
from .predicciones_mensuales import _build_single
from .prioridad_territorial import MIN_INCIDENTES_TERRITORIO, _query_totales_territorio

NivelTerritorio = Literal["comuna", "barrio"]
TipoEspacial = Literal["series_territorial", "ranking_via", "ranking_punto"]
MIN_INCIDENTES_VIA = 5
MIN_INCIDENTES_PUNTO = 3


def _bloque_territorio(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
    nivel: NivelTerritorio,
    territorio_id: int,
    horizonte: int,
    modelo: str,
    excluir_covid: bool,
) -> dict[str, Any] | None:
    f = FiltrosKpi(
        comuna_id=territorio_id if nivel == "comuna" else filtros.comuna_id,
        barrio_id=territorio_id if nivel == "barrio" else None,
        clase_incidente_id=filtros.clase_incidente_id,
    )
    bloque = _build_single(inicio, fin, f, horizonte, modelo, "incidentes", excluir_covid)
    if bloque["meta"].get("sin_modelo"):
        return None
    carga = sum(float(r.get("proyectados") or 0) for r in bloque["proyeccion"])
    return {
        "serie_historica": bloque["serie_historica"],
        "proyeccion": bloque["proyeccion"],
        "carga_proyectada_horizonte": round(carga, 2),
        "meta": {
            "sin_modelo": False,
            "modelo": modelo,
            "r2": bloque["meta"].get("coeficientes", {}).get("r2"),
            "bondad_nivel": bloque["meta"].get("bondad_nivel"),
        },
    }


def _query_totales_via(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
) -> dict[int, dict[str, Any]]:
    where = ["i.fecha_incidente >= %s", "i.fecha_incidente <= %s", "i.via_id IS NOT NULL"]
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
      v.id,
      COALESCE(NULLIF(trim(v.nombre), ''), 'Sin vía') AS nombre,
      COUNT(i.id)::bigint AS incidentes
    FROM incidente i
    INNER JOIN via v ON i.via_id = v.id
    WHERE {wh}
    GROUP BY v.id, v.nombre
    HAVING COUNT(i.id) >= %s
    """
    out: dict[int, dict[str, Any]] = {}
    with connection.cursor() as cursor:
        cursor.execute(sql, params + [MIN_INCIDENTES_VIA])
        for vid, nombre, inc in cursor.fetchall():
            out[int(vid)] = {"nombre": str(nombre), "incidentes": int(inc or 0)}
    return out


def _query_totales_punto_critico(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
) -> dict[int, dict[str, Any]]:
    where = ["i.fecha_incidente >= %s", "i.fecha_incidente <= %s", "i.punto_critico_id IS NOT NULL"]
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
      pc.id,
      COALESCE(NULLIF(trim(pc.nombre), ''), 'Sin punto') AS nombre,
      COALESCE(NULLIF(trim(v.nombre), ''), '') AS via_nombre,
      COUNT(i.id)::bigint AS incidentes
    FROM incidente i
    INNER JOIN punto_critico pc ON i.punto_critico_id = pc.id
    LEFT JOIN via v ON pc.via_id = v.id
    WHERE {wh}
    GROUP BY pc.id, pc.nombre, v.nombre
    HAVING COUNT(i.id) >= %s
    """
    out: dict[int, dict[str, Any]] = {}
    with connection.cursor() as cursor:
        cursor.execute(sql, params + [MIN_INCIDENTES_PUNTO])
        for pid, nombre, via_nombre, inc in cursor.fetchall():
            out[int(pid)] = {
                "nombre": str(nombre),
                "via_nombre": str(via_nombre or ""),
                "incidentes": int(inc or 0),
            }
    return out


def _cobertura_infraestructura(inicio: date, fin: date, filtros: FiltrosKpi) -> dict[str, Any]:
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
      COUNT(*)::bigint AS total,
      COUNT(i.via_id)::bigint AS con_via,
      COUNT(i.punto_critico_id)::bigint AS con_punto
    FROM incidente i
    WHERE {wh}
    """
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        row = cursor.fetchone()
    total = int(row[0] or 0) if row else 0
    con_via = int(row[1] or 0) if row else 0
    con_punto = int(row[2] or 0) if row else 0
    return {
        "incidentes_total": total,
        "con_via_id": con_via,
        "con_punto_critico_id": con_punto,
        "pct_con_via": round(100.0 * con_via / total, 1) if total else 0.0,
        "pct_con_punto": round(100.0 * con_punto / total, 1) if total else 0.0,
    }


def _meta_fase_c(
    tipo: TipoEspacial,
    modelo: str,
    hm: int,
    limite: int,
    cobertura: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "fase": "C",
        "tipo": tipo,
        "modelo_proyeccion": modelo,
        "horizonte_meses": hm,
        "limite": limite,
        "que_mide": (
            "Proyección mensual de incidentes por unidad espacial (territorio, vía o punto crítico), "
            "para comparar evolución y carga futura en el horizonte elegido."
        ),
        "diferencia_p08": (
            "P08 resume con categoría alto/medio/bajo (terciles). Fase C muestra la serie temporal "
            "por entidad o ranking de vías/puntos para alinear con mapa y tops."
        ),
        "interpretacion": (
            "Seleccione una entidad del listado para ver histórico + proyección. "
            "R² y bondad son por serie individual; pueden variar mucho en barrios o vías con pocos meses."
        ),
        "limitaciones": (
            "Proyección descriptiva por entidad; no modelo conjunto con efectos fijos ni pooling. "
            f"Territorios: mín. {MIN_INCIDENTES_TERRITORIO} incidentes; vías: {MIN_INCIDENTES_VIA}; "
            f"puntos: {MIN_INCIDENTES_PUNTO}."
        ),
    }
    if tipo == "series_territorial":
        base["items_p09_p10"] = "P09 comuna · P10 barrio — series mensuales top por carga proyectada."
    else:
        base["items_p11"] = "P11 — ranking de vías o puntos críticos con incidentes en el periodo."
        if cobertura:
            base["cobertura_datos"] = cobertura
    return base


def build_carga_espacial_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
    tipo: str = "series_territorial",
    nivel: str = "comuna",
    horizonte_meses: int = 3,
    modelo: str = "estacional",
    excluir_covid: bool = True,
    limite: int = 8,
    entidad_id: int | None = None,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    hm = max(1, min(12, int(horizonte_meses)))
    limite = min(max(int(limite), 1), 15)
    mod = modelo if modelo in ("ols", "estacional") else "estacional"

    if tipo in ("ranking_via", "via"):
        t: TipoEspacial = "ranking_via"
    elif tipo in ("ranking_punto", "punto", "punto_critico"):
        t = "ranking_punto"
    else:
        t = "series_territorial"

    meta_base = {
        "fecha_inicio": inicio.isoformat(),
        "fecha_fin": fin.isoformat(),
        "excluir_covid": excluir_covid,
        "filtros": {
            "comuna_id": filtros.comuna_id,
            "barrio_id": filtros.barrio_id,
            "clase_incidente_id": filtros.clase_incidente_id,
        },
    }

    if t == "series_territorial":
        niv: NivelTerritorio = "barrio" if nivel == "barrio" else "comuna"
        totales = _query_totales_territorio(inicio, fin, filtros, niv)
        candidatos: list[tuple[int, dict[str, Any]]] = []

        ids_iter = [entidad_id] if entidad_id is not None and entidad_id in totales else None
        if ids_iter is None:
            ids_iter = list(totales.keys())

        for tid in ids_iter:
            bloque = _bloque_territorio(
                inicio, fin, filtros, niv, tid, hm, mod, excluir_covid
            )
            if bloque is None:
                continue
            tinfo = totales[tid]
            item: dict[str, Any] = {
                "carga_proyectada_horizonte": bloque["carga_proyectada_horizonte"],
                "incidentes_periodo": tinfo["incidentes"],
                "serie_historica": bloque["serie_historica"],
                "proyeccion": bloque["proyeccion"],
                "meta": bloque["meta"],
            }
            if niv == "comuna":
                item["comuna_id"] = tid
                item["comuna_nombre"] = tinfo["nombre"]
            else:
                item["barrio_id"] = tid
                item["barrio_nombre"] = tinfo["nombre"]
                item["comuna_nombre"] = tinfo.get("comuna_nombre", "")
            candidatos.append((tid, item))

        candidatos.sort(key=lambda x: -x[1]["carga_proyectada_horizonte"])
        series = [item for _, item in candidatos[:limite]]
        for i, row in enumerate(series, start=1):
            row["rank"] = i

        sin_datos = len(series) == 0
        return {
            "meta": {
                **meta_base,
                "sin_datos": sin_datos,
                "nivel": niv,
                **_meta_fase_c("series_territorial", mod, hm, limite),
            },
            "series": series,
            "ranking": [],
        }

    cobertura = _cobertura_infraestructura(inicio, fin, filtros)
    if t == "ranking_via":
        totales = _query_totales_via(inicio, fin, filtros)
        id_key, nombre_key = "via_id", "via_nombre"
    else:
        totales = _query_totales_punto_critico(inicio, fin, filtros)
        id_key, nombre_key = "punto_critico_id", "punto_critico_nombre"

    filas: list[dict[str, Any]] = []
    for eid, info in totales.items():
        f = FiltrosKpi(
            comuna_id=filtros.comuna_id,
            barrio_id=filtros.barrio_id,
            clase_incidente_id=filtros.clase_incidente_id,
            via_id=eid if t == "ranking_via" else None,
            punto_critico_id=eid if t == "ranking_punto" else None,
        )
        bloque = _build_single(inicio, fin, f, hm, mod, "incidentes", excluir_covid)
        if bloque["meta"].get("sin_modelo"):
            continue
        carga = sum(float(r.get("proyectados") or 0) for r in bloque["proyeccion"])
        row: dict[str, Any] = {
            id_key: eid,
            nombre_key: info["nombre"],
            "incidentes_periodo": info["incidentes"],
            "carga_proyectada_horizonte": round(carga, 2),
            "horizonte_meses": hm,
            "r2": bloque["meta"].get("coeficientes", {}).get("r2"),
        }
        if t == "ranking_punto" and info.get("via_nombre"):
            row["via_nombre"] = info["via_nombre"]
        filas.append(row)

    filas.sort(key=lambda r: r["carga_proyectada_horizonte"], reverse=True)
    ranking: list[dict[str, Any]] = []
    for i, row in enumerate(filas[:limite], start=1):
        row["rank"] = i
        ranking.append(row)

    return {
        "meta": {
            **meta_base,
            "sin_datos": len(ranking) == 0,
            "tipo": t,
            **_meta_fase_c(t, mod, hm, limite, cobertura),
        },
        "series": [],
        "ranking": ranking,
    }
