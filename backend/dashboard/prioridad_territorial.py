"""
P05 — Índice de prioridad territorial compuesto (comuna o barrio).

Combina (con pesos explícitos en meta):
  - frecuencia de incidentes en el periodo;
  - densidad de incidentes por km² (polígono oficial);
  - tendencia mensual (delta de promedios en ventana móvil, atenuada con series cortas);
  - proporción de víctimas fatales;
  - participación en el total de incidentes del periodo.

La tendencia se atenúa si el territorio está por debajo del percentil 25 de frecuencia.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Literal

from django.db import connection

from .evolucion_mensual import _iter_meses_clave
from .kpis import FiltrosKpi, _fatal_sql_expr
from .predicciones_mensuales import MESES_EXCLUIR_COVID_MEDE
from .territorio_sql import (
    append_filtros_territoriales,
    comuna_fk_col,
    barrio_fk_col,
    meta_filtros_dict,
    nota_modo_territorio,
)

NivelTerritorio = Literal["comuna", "barrio"]

MIN_INCIDENTES_COMUNA = 5
MIN_INCIDENTES_BARRIO = 25
MIN_MESES_TENDENCIA = 6
MIN_MESES_TENDENCIA_PLENA = 12
DELTA_VENTANA_MESES = 6
DELTA_VENTANA_MIN = 3

PESOS_COMPONENTES: dict[str, float] = {
    "frecuencia_incidentes": 0.30,
    "densidad_km2": 0.15,
    "tendencia_mensual": 0.20,
    "pct_victimas_fatales": 0.20,
    "participacion": 0.15,
}

VARIANTES_PESOS_SENSIBILIDAD: dict[str, dict[str, float]] = {
    "base": PESOS_COMPONENTES,
    "mas_frecuencia": {
        "frecuencia_incidentes": 0.40,
        "densidad_km2": 0.10,
        "tendencia_mensual": 0.15,
        "pct_victimas_fatales": 0.20,
        "participacion": 0.15,
    },
    "mas_tendencia": {
        "frecuencia_incidentes": 0.22,
        "densidad_km2": 0.10,
        "tendencia_mensual": 0.33,
        "pct_victimas_fatales": 0.20,
        "participacion": 0.15,
    },
}

JUSTIFICACION_PESOS: list[dict[str, Any]] = [
    {
        "componente": "frecuencia_incidentes",
        "peso": PESOS_COMPONENTES["frecuencia_incidentes"],
        "motivo": (
            "Mayor peso porque el volumen absoluto de incidentes en el periodo es el "
            "criterio más directo de carga sobre el sistema."
        ),
    },
    {
        "componente": "densidad_km2",
        "peso": PESOS_COMPONENTES["densidad_km2"],
        "motivo": (
            "Incidentes por km² según polígono oficial (comuna/barrio): corrige territorios "
            "grandes con muchos eventos pero concentración espacial menor."
        ),
    },
    {
        "componente": "tendencia_mensual",
        "peso": PESOS_COMPONENTES["tendencia_mensual"],
        "motivo": (
            "Penaliza territorios con tendencia al alza. Se atenúa si el volumen es bajo "
            "(percentil 25 de frecuencia) o si la serie tiene menos de 12 meses."
        ),
    },
    {
        "componente": "pct_victimas_fatales",
        "peso": PESOS_COMPONENTES["pct_victimas_fatales"],
        "motivo": (
            "Introduce severidad relativa (víctimas fatales sobre víctimas), no solo cantidad "
            "de eventos."
        ),
    },
    {
        "componente": "participacion",
        "peso": PESOS_COMPONENTES["participacion"],
        "motivo": (
            "Menor peso porque es parcialmente redundante con la frecuencia; expresa "
            "concentración proporcional del problema."
        ),
    },
]

TENDENCIA_COMPONENTE_META: dict[str, str] = {
    "modelo": "delta_promedios",
    "etiqueta": "Delta de promedios mensuales (ventana móvil)",
    "por_que_delta": (
        "Por cada territorio se comparan dos tramos de la serie mensual de incidentes: "
        "promedio de los últimos N meses menos promedio de los N meses anteriores. "
        "Valor positivo = empeora (más incidentes recientes). Solo deltas ≥ 0 entran al índice."
    ),
    "reglas_ventana": (
        f"Con ≥ {MIN_MESES_TENDENCIA_PLENA} meses en la serie: N = {DELTA_VENTANA_MESES} fijo "
        f"(últimos {DELTA_VENTANA_MESES} vs los {DELTA_VENTANA_MESES} previos; "
        f"los meses anteriores a ese bloque de {2 * DELTA_VENTANA_MESES} no entran al delta). "
        f"Con {MIN_MESES_TENDENCIA}–{MIN_MESES_TENDENCIA_PLENA - 1} meses: N = mitad de la serie "
        f"(mín. {DELTA_VENTANA_MIN}) y el delta se atenúa × n/{MIN_MESES_TENDENCIA_PLENA}. "
        f"Menos de {MIN_MESES_TENDENCIA} meses: sin delta."
    ),
    "por_que_no_estacional": (
        "La estacionalidad y la proyección formal están en la sección 1 (proyección mensual) "
        "y la anticipación por territorio en la sección 3 (carga esperada). Aquí solo se resume "
        "si el territorio viene subiendo respecto a su propio pasado reciente."
    ),
}

NOTA_TABLERO_VS_P05 = (
    "El tablero descriptivo rankea territorios por conteo de víctimas; este índice (P05) "
    "usa incidentes distintos y un puntaje compuesto. No deben coincidir fila a fila."
)

NOTA_COMPLEMENTO_CARGA = (
    "Para anticipar carga futura por territorio, complemente con la sección 3 "
    "(carga esperada territorial), que proyecta incidentes en el horizonte elegido."
)


def min_incidentes_territorio(nivel: NivelTerritorio) -> int:
    return MIN_INCIDENTES_BARRIO if nivel == "barrio" else MIN_INCIDENTES_COMUNA


def _formula_texto() -> str:
    p = PESOS_COMPONENTES
    return (
        f"índice = {p['frecuencia_incidentes']:.0%}·score(frecuencia) + "
        f"{p['densidad_km2']:.0%}·score(densidad/km²) + "
        f"{p['tendencia_mensual']:.0%}·score(tendencia↑) + "
        f"{p['pct_victimas_fatales']:.0%}·score(% fatales) + "
        f"{p['participacion']:.0%}·score(participación); "
        "cada score normalizado 0–100 entre territorios elegibles."
    )


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
    min_inc = min_incidentes_territorio(nivel)

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
    params.append(min_inc)

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


def _query_area_km2(nivel: NivelTerritorio) -> dict[int, float]:
    tabla = "comuna" if nivel == "comuna" else "barrio"
    sql = f"""
    SELECT id, (ST_Area(geom::geography) / 1e6)::double precision AS area_km2
    FROM {tabla}
    WHERE geom IS NOT NULL
    """
    out: dict[int, float] = {}
    with connection.cursor() as cursor:
        cursor.execute(sql)
        for tid, area in cursor.fetchall():
            a = float(area or 0)
            if a > 0:
                out[int(tid)] = a
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


def _delta_promedios_territorio(meses_vals: list[int]) -> float | None:
    """
    Por territorio: promedio(recentes N meses) - promedio(N meses previos).
    Requiere al menos MIN_MESES_TENDENCIA meses en la serie (tras excluir COVID si aplica).
    """
    n = len(meses_vals)
    if n < MIN_MESES_TENDENCIA:
        return None
    w = DELTA_VENTANA_MESES if n >= MIN_MESES_TENDENCIA_PLENA else max(DELTA_VENTANA_MIN, n // 2)
    if n < 2 * w:
        return None
    reciente = meses_vals[-w:]
    anterior = meses_vals[-2 * w : -w]
    prom_rec = sum(reciente) / w
    prom_ant = sum(anterior) / w
    delta = prom_rec - prom_ant
    if n < MIN_MESES_TENDENCIA_PLENA:
        delta *= n / MIN_MESES_TENDENCIA_PLENA
    return delta


def _percentil_25(valores: list[float]) -> float:
    if not valores:
        return 0.0
    s = sorted(valores)
    idx = max(0, (len(s) - 1) // 4)
    return s[idx]


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


def _tid_row(row: dict[str, Any], niv: NivelTerritorio) -> int:
    return int(row["comuna_id"] if niv == "comuna" else row["barrio_id"])


def _indice_con_pesos(scores: dict[str, float], pesos: dict[str, float]) -> float:
    return sum(pesos.get(k, 0.0) * scores.get(k, 0.0) for k in pesos)


def _top5_territorio_ids(filas: list[dict[str, Any]], pesos: dict[str, float]) -> list[int]:
    ordenados = sorted(
        filas,
        key=lambda r: _indice_con_pesos(r["_scores"], pesos),
        reverse=True,
    )
    return [_tid_row(r, r["_nivel"]) for r in ordenados[:5]]


def _analisis_sensibilidad_pesos(filas: list[dict[str, Any]], niv: NivelTerritorio) -> dict[str, Any]:
    base_top = _top5_territorio_ids(filas, VARIANTES_PESOS_SENSIBILIDAD["base"])
    variantes: list[dict[str, Any]] = []
    for nombre, pesos in VARIANTES_PESOS_SENSIBILIDAD.items():
        if nombre == "base":
            continue
        alt_top = _top5_territorio_ids(filas, pesos)
        overlap = len(set(base_top) & set(alt_top))
        variantes.append(
            {
                "variante": nombre,
                "pesos": pesos,
                "top5": alt_top,
                "coincidencias_con_base": overlap,
            }
        )
    return {
        "top5_base": base_top,
        "variantes": variantes,
        "interpretacion": (
            "Si las variantes comparten 3–5 territorios con la base, el orden del top es estable "
            "ante cambios razonables de pesos."
        ),
    }


def _row_base(
    tid: int,
    t: dict[str, Any],
    niv: NivelTerritorio,
    raw_fatal: float,
    raw_part: float,
    delta_trend: float | None,
    scores: dict[str, float],
    tendencia_atenuada: bool,
    densidad_km2: float | None,
    area_km2: float | None,
) -> dict[str, Any]:
    indice = _indice_con_pesos(scores, PESOS_COMPONENTES)
    delta_round = round(delta_trend, 4) if delta_trend is not None else None
    row: dict[str, Any] = {
        "indice_prioridad": round(indice, 2),
        "incidentes_periodo": t["incidentes"],
        "victimas_periodo": t["victimas"],
        "victimas_fatales_periodo": t["fatales"],
        "pct_victimas_fatales": round(raw_fatal, 2),
        "participacion_incidentes_pct": round(raw_part, 2),
        "delta_promedio_incidentes": delta_round,
        "pendiente_mensual_incidentes": delta_round,
        "densidad_incidentes_km2": round(densidad_km2, 4) if densidad_km2 is not None else None,
        "area_km2": round(area_km2, 4) if area_km2 is not None else None,
        "tendencia_atenuada": tendencia_atenuada,
        "componentes_normalizados": {
            k: round(scores[k], 2) for k in PESOS_COMPONENTES
        },
        "_scores": scores,
        "_nivel": niv,
    }
    if niv == "comuna":
        row["comuna_id"] = tid
        row["comuna_nombre"] = t["nombre"]
    else:
        row["barrio_id"] = tid
        row["barrio_nombre"] = t["nombre"]
        row["comuna_nombre"] = t.get("comuna_nombre", "")
    return row


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
    min_inc = min_incidentes_territorio(niv)

    totales = _query_totales_territorio(inicio, fin, filtros, niv)
    if not totales:
        return {
            "meta": _meta_base(
                inicio, fin, niv, excluir_covid, limite, filtros, sin_datos=True,
            ),
            "ranking": [],
            "ranking_por_frecuencia": [],
        }

    mensual = _query_mensual_por_territorio(inicio, fin, filtros, niv, excluir_covid)
    areas = _query_area_km2(niv)
    total_incidentes_ciudad = sum(t["incidentes"] for t in totales.values())

    raw_freq: dict[int, float] = {}
    raw_trend: dict[int, float] = {}
    raw_fatal: dict[int, float] = {}
    raw_part: dict[int, float] = {}
    raw_dens: dict[int, float] = {}
    deltas: dict[int, float | None] = {}
    tendencia_atenuada: dict[int, bool] = {}

    p25_freq = _percentil_25([float(t["incidentes"]) for t in totales.values()])

    for tid, t in totales.items():
        raw_freq[tid] = float(t["incidentes"])
        raw_part[tid] = (
            100.0 * t["incidentes"] / total_incidentes_ciudad if total_incidentes_ciudad else 0.0
        )
        vic = t["victimas"]
        raw_fatal[tid] = 100.0 * t["fatales"] / vic if vic > 0 else 0.0

        serie = mensual.get(tid, {})
        vals = list(serie.values()) if serie else []
        d = _delta_promedios_territorio(vals)
        deltas[tid] = d
        raw_trend[tid] = max(0.0, d) if d is not None else 0.0

        area = areas.get(tid)
        if area and area > 0:
            raw_dens[tid] = t["incidentes"] / area
        else:
            raw_dens[tid] = 0.0

    score_freq = _normalizar_0_100(raw_freq)
    score_trend = _normalizar_0_100(raw_trend)
    score_fatal = _normalizar_0_100(raw_fatal)
    score_part = _normalizar_0_100(raw_part)
    score_dens = _normalizar_0_100(raw_dens) if any(v > 0 for v in raw_dens.values()) else {k: 0.0 for k in raw_freq}

    for tid in score_trend:
        atenuada = False
        if p25_freq > 0 and raw_freq[tid] < p25_freq:
            factor = raw_freq[tid] / p25_freq
            score_trend[tid] *= factor
            atenuada = True
        tendencia_atenuada[tid] = atenuada

    filas: list[dict[str, Any]] = []
    for tid, t in totales.items():
        scores = {
            "frecuencia_incidentes": score_freq.get(tid, 0.0),
            "densidad_km2": score_dens.get(tid, 0.0),
            "tendencia_mensual": score_trend.get(tid, 0.0),
            "pct_victimas_fatales": score_fatal.get(tid, 0.0),
            "participacion": score_part.get(tid, 0.0),
        }
        area = areas.get(tid)
        dens = raw_dens.get(tid) if raw_dens.get(tid, 0) > 0 else None
        filas.append(
            _row_base(
                tid,
                t,
                niv,
                raw_fatal[tid],
                raw_part[tid],
                deltas[tid],
                scores,
                tendencia_atenuada.get(tid, False),
                dens,
                area,
            )
        )

    by_freq = sorted(filas, key=lambda r: r["incidentes_periodo"], reverse=True)
    freq_rank_map = {_tid_row(r, niv): i + 1 for i, r in enumerate(by_freq)}

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

    def _public_row(row: dict[str, Any], rank: int, nivel_prio: str) -> dict[str, Any]:
        out = {k: v for k, v in row.items() if not k.startswith("_")}
        out["rank"] = rank
        out["nivel_prioridad"] = nivel_prio
        out["rank_frecuencia"] = freq_rank_map.get(_tid_row(row, niv), rank)
        return out

    ranking: list[dict[str, Any]] = []
    for i, row in enumerate(filas[:limite], start=1):
        ranking.append(
            _public_row(row, i, _nivel_tercil(row["indice_prioridad"], p33, p66))
        )

    ranking_frec: list[dict[str, Any]] = []
    for i, row in enumerate(by_freq[:limite], start=1):
        comp_row = next(r for r in filas if _tid_row(r, niv) == _tid_row(row, niv))
        ranking_frec.append(
            _public_row(comp_row, i, _nivel_tercil(comp_row["indice_prioridad"], p33, p66))
        )

    sensibilidad = _analisis_sensibilidad_pesos(filas, niv)
    alerta = _alerta_liderazgo(ranking)

    meta = _meta_base(
        inicio,
        fin,
        niv,
        excluir_covid,
        limite,
        filtros,
        sin_datos=False,
        total_territorios=len(totales),
        total_incidentes=total_incidentes_ciudad,
        min_inc=min_inc,
        umbrales={
            "alto": f"índice ≥ {p66:.2f} (tercil superior)",
            "medio": f"entre {p33:.2f} y {p66:.2f}",
            "bajo": f"índice < {p33:.2f}",
        },
        sensibilidad=sensibilidad,
        alerta_liderazgo=alerta,
        p25_frecuencia_incidentes=round(p25_freq, 2),
    )
    return {
        "meta": meta,
        "ranking": ranking,
        "ranking_por_frecuencia": ranking_frec,
    }


def _alerta_liderazgo(ranking: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not ranking:
        return None
    top = ranking[0]
    rf = int(top.get("rank_frecuencia") or 1)
    if rf <= 5:
        return None
    nombre = top.get("comuna_nombre") or top.get("barrio_nombre") or "Territorio"
    return {
        "tipo": "no_lidera_por_volumen",
        "rank_frecuencia": rf,
        "mensaje": (
            f"«{nombre}» lidera el índice compuesto pero ocupa el puesto {rf} por número de "
            "incidentes en el periodo: el orden lo empujan tendencia, densidad o gravedad. "
            "Contraste con la vista «Solo por frecuencia»."
        ),
    }


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
    min_inc: int | None = None,
    umbrales: dict[str, str] | None = None,
    sensibilidad: dict[str, Any] | None = None,
    alerta_liderazgo: dict[str, Any] | None = None,
    p25_frecuencia_incidentes: float | None = None,
) -> dict[str, Any]:
    min_inc = min_inc if min_inc is not None else min_incidentes_territorio(niv)
    meta: dict[str, Any] = {
        "fecha_inicio": inicio.isoformat(),
        "fecha_fin": fin.isoformat(),
        "nivel": niv,
        "sin_datos": sin_datos,
        "limite": limite,
        "total_territorios_elegibles": total_territorios,
        "total_incidentes_periodo": total_incidentes,
        "excluir_covid_tendencia": excluir_covid,
        "min_incidentes_territorio": min_inc,
        "min_incidentes_comuna": MIN_INCIDENTES_COMUNA,
        "min_incidentes_barrio": MIN_INCIDENTES_BARRIO,
        "pesos": PESOS_COMPONENTES,
        "justificacion_pesos": JUSTIFICACION_PESOS,
        "tendencia_componente": TENDENCIA_COMPONENTE_META,
        "formula": _formula_texto(),
        "limitaciones": _limitaciones_texto(niv, min_inc),
        "nota_tablero_vs_p05": NOTA_TABLERO_VS_P05,
        "nota_complemento_carga_esperada": NOTA_COMPLEMENTO_CARGA,
        "filtros": meta_filtros_dict(filtros),
        "nota_territorio": nota_modo_territorio(filtros.modo_territorio),
    }
    if umbrales:
        meta["umbrales_nivel"] = umbrales
    if sensibilidad:
        meta["sensibilidad_pesos"] = sensibilidad
    if alerta_liderazgo:
        meta["alerta_liderazgo"] = alerta_liderazgo
    if p25_frecuencia_incidentes is not None:
        meta["p25_frecuencia_incidentes"] = p25_frecuencia_incidentes
    return meta


def _limitaciones_texto(niv: NivelTerritorio, min_inc: int) -> str:
    return (
        "Índice compuesto descriptivo para priorizar territorios en el periodo filtrado; "
        "no implica causalidad ni riesgo individual. La tendencia usa delta de promedios mensuales "
        f"(mín. {MIN_MESES_TENDENCIA} meses; ventana {DELTA_VENTANA_MESES} meses si hay ≥ "
        f"{MIN_MESES_TENDENCIA_PLENA}); territorios con menos de {min_inc} incidentes quedan fuera "
        f"({'barrio' if niv == 'barrio' else 'comuna'}). "
        "La densidad depende del área del polígono oficial. No sustituye estudios de seguridad vial."
    )


# Compatibilidad con imports antiguos
MIN_INCIDENTES_TERRITORIO = MIN_INCIDENTES_COMUNA
