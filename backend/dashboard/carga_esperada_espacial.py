"""
Fase C — series mensuales por comuna/barrio (P09/P10) vía API espacial.

P11 (ranking por vía o punto crítico) quedó fuera del alcance del producto: no hay UI
ni catálogo ETL de vías/puntos críticos. El endpoint se conserva solo como código legacy.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Literal

from django.db import connection

from .kpis import FiltrosKpi
from .predicciones_mensuales import (
    MA_VENTANA_DEFAULT,
    _build_single,
    normalize_modelo_proyeccion,
)
from .prioridad_territorial import MIN_INCIDENTES_TERRITORIO, _query_totales_territorio
from .territorio_sql import (
    append_filtros_territoriales,
    dwithin_incidente_punto_sql,
    meta_filtros_dict,
    nota_modo_punto_critico,
    nota_modo_territorio,
    parse_modo_punto_critico,
)

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
    ventana_ma: int = MA_VENTANA_DEFAULT,
) -> dict[str, Any] | None:
    f = FiltrosKpi(
        comuna_id=territorio_id if nivel == "comuna" else filtros.comuna_id,
        barrio_id=territorio_id if nivel == "barrio" else None,
        clase_incidente_id=filtros.clase_incidente_id,
        modo_territorio=filtros.modo_territorio,
    )
    bloque = _build_single(
        inicio,
        fin,
        f,
        horizonte,
        modelo,  # type: ignore[arg-type]
        "incidentes",
        excluir_covid,
        ventana_ma=ventana_ma,
    )
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
    append_filtros_territoriales(where, params, filtros)
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
    modo_punto: str = "registro",
) -> dict[int, dict[str, Any]]:
    modo = parse_modo_punto_critico(modo_punto)
    if modo == "proximidad":
        return _query_totales_punto_proximidad(inicio, fin, filtros)
    return _query_totales_punto_registro(inicio, fin, filtros)


def _query_totales_punto_registro(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
) -> dict[int, dict[str, Any]]:
    where = ["i.fecha_incidente >= %s", "i.fecha_incidente <= %s", "i.punto_critico_id IS NOT NULL"]
    params: list[Any] = [inicio, fin]
    append_filtros_territoriales(where, params, filtros)
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
                "incidentes_registro": int(inc or 0),
            }
    return out


def _query_totales_punto_proximidad(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
) -> dict[int, dict[str, Any]]:
    where = [
        "i.fecha_incidente >= %s",
        "i.fecha_incidente <= %s",
        "i.ubicacion IS NOT NULL",
        "pc.ubicacion IS NOT NULL",
        dwithin_incidente_punto_sql(),
    ]
    params: list[Any] = [inicio, fin]
    append_filtros_territoriales(where, params, filtros)
    wh = " AND ".join(where)
    sql = f"""
    SELECT
      pc.id,
      COALESCE(NULLIF(trim(pc.nombre), ''), 'Sin punto') AS nombre,
      COALESCE(NULLIF(trim(v.nombre), ''), '') AS via_nombre,
      COUNT(DISTINCT i.id)::bigint AS incidentes,
      COUNT(DISTINCT i.id) FILTER (WHERE i.punto_critico_id = pc.id)::bigint AS incidentes_registro
    FROM punto_critico pc
    INNER JOIN incidente i ON TRUE
    LEFT JOIN via v ON pc.via_id = v.id
    WHERE {wh}
    GROUP BY pc.id, pc.nombre, v.nombre
    HAVING COUNT(DISTINCT i.id) >= %s
    """
    out: dict[int, dict[str, Any]] = {}
    with connection.cursor() as cursor:
        cursor.execute(sql, params + [MIN_INCIDENTES_PUNTO])
        for pid, nombre, via_nombre, inc, inc_reg in cursor.fetchall():
            out[int(pid)] = {
                "nombre": str(nombre),
                "via_nombre": str(via_nombre or ""),
                "incidentes": int(inc or 0),
                "incidentes_registro": int(inc_reg or 0),
            }
    return out


def _cobertura_infraestructura(inicio: date, fin: date, filtros: FiltrosKpi) -> dict[str, Any]:
    where = ["i.fecha_incidente >= %s", "i.fecha_incidente <= %s"]
    params: list[Any] = [inicio, fin]
    append_filtros_territoriales(where, params, filtros)
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


def _catalogo_infra_counts() -> dict[str, int]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT
              (SELECT count(*)::bigint FROM via),
              (SELECT count(*)::bigint FROM punto_critico),
              (SELECT count(*)::bigint FROM punto_critico WHERE ubicacion IS NOT NULL)
            """
        )
        row = cursor.fetchone()
    n_vias, n_puntos, n_puntos_ub = (int(x or 0) for x in row)
    return {
        "n_vias": n_vias,
        "n_puntos_criticos": n_puntos,
        "n_puntos_con_ubicacion": n_puntos_ub,
    }


def _motivo_sin_ranking_p11(tipo: TipoEspacial, catalogo: dict[str, int], modo_punto: str) -> str | None:
    if tipo == "ranking_via":
        if catalogo["n_vias"] == 0:
            return (
                "El catálogo `via` está vacío y ningún incidente tiene `via_id` en la base. "
                "P11 no puede rankear vías hasta cargar vías normalizadas y enlazarlas en el ETL de Mede."
            )
        return None
    if catalogo["n_puntos_criticos"] == 0:
        return (
            "El catálogo `punto_critico` está vacío. "
            "Cargue puntos críticos (nombre, coordenadas, radio) antes de usar P11."
        )
    if parse_modo_punto_critico(modo_punto) == "proximidad" and catalogo["n_puntos_con_ubicacion"] == 0:
        return (
            "Hay puntos críticos en catálogo pero ninguno tiene `ubicacion` PostGIS. "
            "Ejecute el script 003_punto_critico_ubicacion.sql o complete latitud/longitud."
        )
    return None


def _meta_fase_c(
    tipo: TipoEspacial,
    modelo: str,
    hm: int,
    limite: int,
    cobertura: dict[str, Any] | None = None,
    modo_punto: str = "registro",
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
        "limitaciones": (
            "Proyección descriptiva por entidad; no modelo conjunto con efectos fijos ni pooling. "
            f"Territorios: mín. {MIN_INCIDENTES_TERRITORIO} incidentes; vías: {MIN_INCIDENTES_VIA}; "
            f"puntos: {MIN_INCIDENTES_PUNTO}."
        ),
    }
    if tipo == "series_territorial":
        base["items_p09_p10"] = "P09 comuna · P10 barrio — series mensuales top por carga proyectada."
        base["interpretacion"] = (
            "Seleccione una entidad del listado para ver histórico + proyección. "
            "R² y bondad son por serie individual; pueden variar mucho en barrios con pocos meses."
        )
    elif tipo == "ranking_via":
        base["items_p11"] = "P11 — ranking de vías con incidentes en el periodo."
        base["que_mide"] = (
            "Carga proyectada de incidentes por vía en el horizonte elegido, ordenada de mayor a menor."
        )
        base["interpretacion"] = (
            f"Lista las vías con al menos {MIN_INCIDENTES_VIA} incidentes en el periodo y serie mensual "
            f"suficiente para proyectar los próximos {hm} mes(es). R² indica qué tan bien el modelo "
            "estacional/OLS explica la serie de cada vía (puede ser bajo con pocas observaciones)."
        )
        if cobertura:
            base["cobertura_datos"] = cobertura
    else:
        base["items_p11"] = "P11 — ranking de puntos críticos con incidentes en el periodo."
        base["que_mide"] = (
            "Carga proyectada de incidentes asociada a cada punto crítico en el horizonte elegido."
        )
        base["interpretacion"] = (
            f"Ordena puntos críticos con al menos {MIN_INCIDENTES_PUNTO} incidentes en el periodo. "
            f"La proyección suma los próximos {hm} mes(es) con el mismo filtro de asignación "
            "(registro Mede o proximidad espacial). Compare R² solo como guía de estabilidad de la serie."
        )
        base["modo_punto"] = parse_modo_punto_critico(modo_punto)
        base["nota_modo_punto"] = nota_modo_punto_critico(modo_punto)
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
    modo_punto: str = "registro",
    ventana_ma: int = MA_VENTANA_DEFAULT,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    modo_punto_norm = parse_modo_punto_critico(modo_punto)
    hm = max(1, min(12, int(horizonte_meses)))
    limite = min(max(int(limite), 1), 15)
    mod = normalize_modelo_proyeccion(modelo)

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
        "filtros": meta_filtros_dict(filtros),
        "nota_territorio": nota_modo_territorio(filtros.modo_territorio),
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
                inicio, fin, filtros, niv, tid, hm, mod, excluir_covid, ventana_ma
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
    catalogo = _catalogo_infra_counts()
    motivo = _motivo_sin_ranking_p11(t, catalogo, modo_punto_norm)
    if t == "ranking_via":
        totales = _query_totales_via(inicio, fin, filtros)
        id_key, nombre_key = "via_id", "via_nombre"
    else:
        totales = _query_totales_punto_critico(inicio, fin, filtros, modo_punto_norm)
        id_key, nombre_key = "punto_critico_id", "punto_critico_nombre"

    filas: list[dict[str, Any]] = []
    for eid, info in totales.items():
        f = FiltrosKpi(
            comuna_id=filtros.comuna_id,
            barrio_id=filtros.barrio_id,
            clase_incidente_id=filtros.clase_incidente_id,
            via_id=eid if t == "ranking_via" else None,
            punto_critico_id=eid if t == "ranking_punto" else None,
            modo_territorio=filtros.modo_territorio,
            punto_critico_modo=modo_punto_norm if t == "ranking_punto" else "registro",
        )
        bloque = _build_single(
            inicio,
            fin,
            f,
            hm,
            mod,  # type: ignore[arg-type]
            "incidentes",
            excluir_covid,
            ventana_ma=ventana_ma,
        )
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
        if t == "ranking_punto":
            if info.get("incidentes_registro") is not None:
                row["incidentes_registro_fk"] = info["incidentes_registro"]
            if modo_punto_norm == "proximidad" and info.get("incidentes_registro") is not None:
                extra = info["incidentes"] - info["incidentes_registro"]
                if extra > 0:
                    row["incidentes_solo_proximidad"] = extra
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
            "catalogo_infra": catalogo,
            **({"motivo_sin_datos": motivo, "sin_catalogo": True} if motivo else {}),
            **_meta_fase_c(t, mod, hm, limite, cobertura, modo_punto_norm),
        },
        "series": [],
        "ranking": ranking,
    }
