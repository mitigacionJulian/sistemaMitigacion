"""
P05 — Índice de prioridad territorial compuesto (comuna o barrio).

Combina (con pesos explícitos en meta):
  - frecuencia de incidentes en el periodo;
  - tendencia mensual (pendiente OLS sobre conteos mensuales);
  - proporción de víctimas fatales;
  - participación en el total de incidentes del periodo (ciudad o comuna filtrada).
"""
from __future__ import annotations

from datetime import date
from typing import Any, Literal

from django.db import connection

from .evolucion_mensual import _iter_meses_clave
from .kpis import FiltrosKpi, _fatal_sql_expr
from .predicciones_mensuales import MESES_EXCLUIR_COVID_MEDE, _ols_intercept_slope
from .territorio_sql import (
    append_filtros_territoriales,
    comuna_fk_col,
    barrio_fk_col,
    meta_filtros_dict,
    nota_modo_territorio,
)

NivelTerritorio = Literal["comuna", "barrio"]

MIN_INCIDENTES_TERRITORIO = 5
MIN_MESES_TENDENCIA = 3

PESOS_COMPONENTES: dict[str, float] = {
    "frecuencia_incidentes": 0.35,
    "tendencia_mensual": 0.25,
    "pct_victimas_fatales": 0.25,
    "participacion": 0.15,
}

# Textos de sustentación (también en docs/PREDICCIONES_GUIA_SUSTENTACION.md §10)
JUSTIFICACION_PESOS: list[dict[str, Any]] = [
    {
        "componente": "frecuencia_incidentes",
        "peso": 0.35,
        "motivo": (
            "Mayor peso porque el volumen absoluto de incidentes en el periodo es el "
            "criterio más directo de carga sobre el sistema y coincide con la lectura "
            "operativa habitual (dónde ocurren más siniestros)."
        ),
    },
    {
        "componente": "tendencia_mensual",
        "peso": 0.25,
        "motivo": (
            "Penaliza territorios con tendencia al alza aunque hoy no sean los más grandes: "
            "anticipa deterioro. Mismo peso que gravedad para equilibrar magnitud y evolución."
        ),
    },
    {
        "componente": "pct_victimas_fatales",
        "peso": 0.25,
        "motivo": (
            "Introduce severidad relativa (víctimas fatales sobre víctimas), no solo cantidad "
            "de eventos. Relevante para priorización con enfoque en daño humano."
        ),
    },
    {
        "componente": "participacion",
        "peso": 0.15,
        "motivo": (
            "Menor peso porque es parcialmente redundante con la frecuencia, pero ayuda a "
            "expresar concentración proporcional del problema en el territorio analizado."
        ),
    },
]

TENDENCIA_COMPONENTE_META: dict[str, str] = {
    "modelo": "ols",
    "etiqueta": "Pendiente OLS sobre conteos mensuales",
    "por_que_ols": (
        "En P05 la tendencia es un subindicador interno del ranking, no la proyección "
        "mostrada al usuario: se necesita una pendiente simple y comparable entre decenas "
        "de comunas con series de distinta longitud. OLS cumple eso con pocos datos (≥3 meses)."
    ),
    "por_que_no_estacional": (
        "El modelo estacional (P02) exige más parámetros (mes calendario, a veces año) y "
        "estabilidad por territorio; en barrios/comunas con series cortas o irregulares "
        "sobreajusta o no converge. La estacionalidad ya está cubierta en el bloque de "
        "«Predicciones» a nivel ciudad; aquí se prioriza parsimonia y comparabilidad."
    ),
}


def _where_sql(filtros: FiltrosKpi, nivel: NivelTerritorio) -> tuple[str, list[Any]]:
    where = ["i.fecha_incidente >= %s", "i.fecha_incidente <= %s"]
    params: list[Any] = []
    col_c = comuna_fk_col(filtros.modo_territorio)
    col_b = barrio_fk_col(filtros.modo_territorio)
    if nivel == "comuna":
        where.append(f"i.{col_c} IS NOT NULL")
    else:
        where.append(f"i.{col_b} IS NOT NULL")
    append_filtros_territoriales(where, params, filtros)
    return " AND ".join(where), params


def _query_totales_territorio(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
    nivel: NivelTerritorio,
) -> dict[int, dict[str, Any]]:
    wh, base_params = _where_sql(filtros, nivel)
    params = [inicio, fin] + base_params
    fatal = _fatal_sql_expr("gv")

    col_c = comuna_fk_col(filtros.modo_territorio)
    col_b = barrio_fk_col(filtros.modo_territorio)

    if nivel == "comuna":
        id_sql = f"i.{col_c}"
        name_sql = "COALESCE(NULLIF(trim(co.nombre), ''), 'Sin comuna')"
        joins = f"LEFT JOIN comuna co ON i.{col_c} = co.id"
        group = f"i.{col_c}, co.nombre"
    else:
        id_sql = f"i.{col_b}"
        name_sql = "COALESCE(NULLIF(trim(b.nombre), ''), 'Sin barrio')"
        joins = f"""
        LEFT JOIN barrio b ON i.{col_b} = b.id
        LEFT JOIN comuna co ON b.comuna_id = co.id
        """
        group = f"i.{col_b}, b.nombre, co.nombre"

    sql = f"""
    SELECT
      {id_sql} AS territorio_id,
      {name_sql} AS nombre,
      COUNT(DISTINCT i.id)::bigint AS incidentes,
      COUNT(v.id)::bigint AS victimas,
      COALESCE(SUM(CASE WHEN {fatal} THEN 1 ELSE 0 END), 0)::bigint AS fatales
      {", COALESCE(NULLIF(trim(co.nombre), ''), '') AS comuna_nombre" if nivel == "barrio" else ""}
    FROM incidente i
    LEFT JOIN victima v ON v.incidente_id = i.id
    LEFT JOIN gravedad_victima gv ON v.gravedad_victima_id = gv.id
    {joins}
    WHERE {wh}
    GROUP BY {group}
    HAVING COUNT(DISTINCT i.id) >= %s
    """
    params.append(MIN_INCIDENTES_TERRITORIO)

    out: dict[int, dict[str, Any]] = {}
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        cols = [c[0] for c in cursor.description]
        for row in cursor.fetchall():
            rec = dict(zip(cols, row))
            tid = int(rec["territorio_id"])
            item: dict[str, Any] = {
                "incidentes": int(rec["incidentes"] or 0),
                "victimas": int(rec["victimas"] or 0),
                "fatales": int(rec["fatales"] or 0),
                "nombre": str(rec["nombre"] or ""),
            }
            if nivel == "barrio":
                item["comuna_nombre"] = str(rec.get("comuna_nombre") or "")
            out[tid] = item
    return out


def _query_mensual_por_territorio(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
    nivel: NivelTerritorio,
    excluir_covid: bool,
) -> dict[int, dict[str, int]]:
    wh, base_params = _where_sql(filtros, nivel)
    params = [inicio, fin] + base_params
    col_c = comuna_fk_col(filtros.modo_territorio)
    col_b = barrio_fk_col(filtros.modo_territorio)
    id_sql = f"i.{col_c}" if nivel == "comuna" else f"i.{col_b}"

    sql = f"""
    SELECT
      {id_sql} AS territorio_id,
      to_char(i.fecha_incidente, 'YYYY-MM') AS mes,
      COUNT(DISTINCT i.id)::bigint AS incidentes
    FROM incidente i
    WHERE {wh}
    GROUP BY {id_sql}, to_char(i.fecha_incidente, 'YYYY-MM')
    ORDER BY territorio_id, mes
    """
    excl = MESES_EXCLUIR_COVID_MEDE if excluir_covid else frozenset()
    meses_rango = _iter_meses_clave(inicio, fin)
    raw: dict[int, dict[str, int]] = {}
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        for tid, mes, cnt in cursor.fetchall():
            if mes in excl:
                continue
            t = int(tid)
            raw.setdefault(t, {})[str(mes)] = int(cnt or 0)

    out: dict[int, dict[str, int]] = {}
    for tid, por_mes in raw.items():
        out[tid] = {mk: por_mes.get(mk, 0) for mk in meses_rango if mk not in excl}
    return out


def _pendiente_territorio(meses_vals: list[int]) -> float | None:
    n = len(meses_vals)
    if n < MIN_MESES_TENDENCIA:
        return None
    xs = [float(i) for i in range(n)]
    ys = [float(v) for v in meses_vals]
    _, b = _ols_intercept_slope(xs, ys)
    return b


def _normalizar_0_100(valores: dict[int, float], invertir: bool = False) -> dict[int, float]:
    if not valores:
        return {}
    lo = min(valores.values())
    hi = max(valores.values())
    if hi - lo < 1e-12:
        return {k: (100.0 if v > 0 else 0.0) for k, v in valores.items()}
    out: dict[int, float] = {}
    for k, v in valores.items():
        s = 100.0 * (v - lo) / (hi - lo)
        out[k] = 100.0 - s if invertir else s
    return out


def _nivel_tercil(indice: float, p33: float, p66: float) -> str:
    if indice >= p66:
        return "alto"
    if indice >= p33:
        return "medio"
    return "bajo"


def build_prioridad_territorial_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
    nivel: str = "comuna",
    limite: int = 15,
    excluir_covid: bool = True,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    niv: NivelTerritorio = "barrio" if nivel == "barrio" else "comuna"
    limite = min(max(int(limite), 1), 50)

    totales = _query_totales_territorio(inicio, fin, filtros, niv)
    if not totales:
        return {
            "meta": _meta_base(inicio, fin, niv, excluir_covid, limite, filtros, sin_datos=True),
            "ranking": [],
        }

    mensual = _query_mensual_por_territorio(inicio, fin, filtros, niv, excluir_covid)
    total_incidentes_ciudad = sum(t["incidentes"] for t in totales.values())

    raw_freq: dict[int, float] = {}
    raw_trend: dict[int, float] = {}
    raw_fatal: dict[int, float] = {}
    raw_part: dict[int, float] = {}
    pendientes: dict[int, float | None] = {}

    for tid, t in totales.items():
        raw_freq[tid] = float(t["incidentes"])
        raw_part[tid] = (
            100.0 * t["incidentes"] / total_incidentes_ciudad if total_incidentes_ciudad else 0.0
        )
        vic = t["victimas"]
        raw_fatal[tid] = 100.0 * t["fatales"] / vic if vic > 0 else 0.0

        serie = mensual.get(tid, {})
        vals = list(serie.values()) if serie else []
        b = _pendiente_territorio(vals)
        pendientes[tid] = b
        raw_trend[tid] = max(0.0, b) if b is not None else 0.0

    score_freq = _normalizar_0_100(raw_freq)
    score_trend = _normalizar_0_100(raw_trend)
    score_fatal = _normalizar_0_100(raw_fatal)
    score_part = _normalizar_0_100(raw_part)

    filas: list[dict[str, Any]] = []
    for tid, t in totales.items():
        sf = score_freq.get(tid, 0.0)
        st = score_trend.get(tid, 0.0)
        sfa = score_fatal.get(tid, 0.0)
        sp = score_part.get(tid, 0.0)
        indice = (
            PESOS_COMPONENTES["frecuencia_incidentes"] * sf
            + PESOS_COMPONENTES["tendencia_mensual"] * st
            + PESOS_COMPONENTES["pct_victimas_fatales"] * sfa
            + PESOS_COMPONENTES["participacion"] * sp
        )
        row: dict[str, Any] = {
            "indice_prioridad": round(indice, 2),
            "incidentes_periodo": t["incidentes"],
            "victimas_periodo": t["victimas"],
            "victimas_fatales_periodo": t["fatales"],
            "pct_victimas_fatales": round(raw_fatal[tid], 2),
            "participacion_incidentes_pct": round(raw_part[tid], 2),
            "pendiente_mensual_incidentes": (
                round(pendientes[tid], 4) if pendientes[tid] is not None else None
            ),
            "componentes_normalizados": {
                "frecuencia_incidentes": round(sf, 2),
                "tendencia_mensual": round(st, 2),
                "pct_victimas_fatales": round(sfa, 2),
                "participacion": round(sp, 2),
            },
        }
        if niv == "comuna":
            row["comuna_id"] = tid
            row["comuna_nombre"] = t["nombre"]
        else:
            row["barrio_id"] = tid
            row["barrio_nombre"] = t["nombre"]
            row["comuna_nombre"] = t.get("comuna_nombre", "")
        filas.append(row)

    filas.sort(key=lambda r: r["indice_prioridad"], reverse=True)
    indices = [r["indice_prioridad"] for r in filas]
    if len(indices) >= 3:
        sorted_i = sorted(indices)
        p33 = sorted_i[len(sorted_i) // 3]
        p66 = sorted_i[(2 * len(sorted_i)) // 3]
    elif indices:
        p33 = min(indices)
        p66 = max(indices)
    else:
        p33 = p66 = 0.0

    ranking: list[dict[str, Any]] = []
    for i, row in enumerate(filas[:limite], start=1):
        row["rank"] = i
        row["nivel_prioridad"] = _nivel_tercil(row["indice_prioridad"], p33, p66)
        ranking.append(row)

    meta = _meta_base(
        inicio, fin, niv, excluir_covid, limite, filtros, sin_datos=False,
        total_territorios=len(totales), total_incidentes=total_incidentes_ciudad,
        umbrales={"alto": f"índice ≥ {p66:.2f} (tercil superior)", "medio": f"entre {p33:.2f} y {p66:.2f}", "bajo": f"índice < {p33:.2f}"},
    )
    return {"meta": meta, "ranking": ranking}


def _meta_base(
    inicio: date,
    fin: date,
    niv: NivelTerritorio,
    excluir_covid: bool,
    limite: int,
    filtros: FiltrosKpi,
    sin_datos: bool,
    total_territorios: int = 0,
    total_incidentes: int = 0,
    umbrales: dict[str, str] | None = None,
) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "fecha_inicio": inicio.isoformat(),
        "fecha_fin": fin.isoformat(),
        "nivel": niv,
        "sin_datos": sin_datos,
        "limite": limite,
        "total_territorios_elegibles": total_territorios,
        "total_incidentes_periodo": total_incidentes,
        "excluir_covid_tendencia": excluir_covid,
        "min_incidentes_territorio": MIN_INCIDENTES_TERRITORIO,
        "pesos": PESOS_COMPONENTES,
        "justificacion_pesos": JUSTIFICACION_PESOS,
        "tendencia_componente": TENDENCIA_COMPONENTE_META,
        "formula": (
            "indice = 0,35·score(frecuencia) + 0,25·score(tendencia↑) + "
            "0,25·score(% fatales) + 0,15·score(participación); "
            "cada score normalizado 0–100 entre territorios del ranking."
        ),
        "limitaciones": _limitaciones_texto(),
        "filtros": meta_filtros_dict(filtros),
        "nota_territorio": nota_modo_territorio(filtros.modo_territorio),
    }
    if umbrales:
        meta["umbrales_nivel"] = umbrales
    return meta


def _limitaciones_texto() -> str:
    return (
        "Índice compuesto descriptivo para priorizar territorios en el periodo filtrado; "
        "no implica causalidad ni riesgo individual. La tendencia usa OLS sobre meses "
        f"(mín. {MIN_MESES_TENDENCIA} meses); territorios con menos de "
        f"{MIN_INCIDENTES_TERRITORIO} incidentes quedan fuera. No sustituye estudios de seguridad vial."
    )
