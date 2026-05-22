"""
P07 — Proporción mensual de víctimas fatales (% sobre víctimas del mes).

Modelos: OLS sobre el % (v1 simple), logit-lineal (logística agregada), estacional sobre el %.
"""
from __future__ import annotations

import math
from datetime import date
from typing import Any, Literal

from django.db import connection

from .evolucion_mensual import _etiqueta_mes_ym, _iter_meses_clave
from .kpis import FiltrosKpi, _fatal_sql_expr
from .predicciones_mensuales import (
    MESES_EXCLUIR_COVID_MEDE,
    _SerieMensual,
    _design_ctx_from_meses,
    _design_forecast_row,
    _fit_estacional,
    _interpretacion_bondad,
    _metricas_ajuste,
    _min_meses_modelo,
    _month_index,
    _next_month_clave,
    _ols_intercept_slope,
    _year_from_ym,
)

ModeloProp = Literal["ols", "logistica", "estacional"]
MIN_VICTIMAS_MES = 10


def _where_sql(filtros: FiltrosKpi, comuna_id: int | None) -> tuple[str, list[Any]]:
    where = ["i.fecha_incidente >= %s", "i.fecha_incidente <= %s"]
    params: list[Any] = []
    if comuna_id is not None:
        where.append("i.comuna_id = %s")
        params.append(comuna_id)
    elif filtros.comuna_id is not None:
        where.append("i.comuna_id = %s")
        params.append(filtros.comuna_id)
    if filtros.barrio_id is not None:
        where.append("i.barrio_id = %s")
        params.append(filtros.barrio_id)
    if filtros.clase_incidente_id is not None:
        where.append("i.clase_incidente_id = %s")
        params.append(filtros.clase_incidente_id)
    return " AND ".join(where), params


def _query_victimas_fatales_mes(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
    comuna_id: int | None = None,
) -> dict[str, dict[str, int]]:
    wh, base_params = _where_sql(filtros, comuna_id)
    fatal = _fatal_sql_expr("gv")
    params = [inicio, fin] + base_params
    sql = f"""
    SELECT
      to_char(i.fecha_incidente, 'YYYY-MM') AS mes,
      COUNT(v.id)::bigint AS victimas,
      COALESCE(SUM(CASE WHEN {fatal} THEN 1 ELSE 0 END), 0)::bigint AS fatales
    FROM incidente i
    INNER JOIN victima v ON v.incidente_id = i.id
    LEFT JOIN gravedad_victima gv ON v.gravedad_victima_id = gv.id
    WHERE {wh}
    GROUP BY to_char(i.fecha_incidente, 'YYYY-MM')
    ORDER BY mes
    """
    out: dict[str, dict[str, int]] = {}
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        for mes, vic, fat in cursor.fetchall():
            out[str(mes)] = {"victimas": int(vic or 0), "fatales": int(fat or 0)}
    return out


def _pct_fatales(victimas: int, fatales: int) -> float | None:
    if victimas < MIN_VICTIMAS_MES:
        return None
    return 100.0 * fatales / victimas


def _logit(p: float) -> float:
    p = max(1e-4, min(1.0 - 1e-4, p / 100.0))
    return math.log(p / (1.0 - p))


def _inv_logit_pct(x: float) -> float:
    return 100.0 / (1.0 + math.exp(-max(-20.0, min(20.0, x))))


def _fit_logistica_lineal(meses: list[str], pcts: list[float]) -> tuple[list[float], list[float], dict[str, Any]]:
    n = len(pcts)
    zs = [_logit(p) for p in pcts]
    xs = [float(i) for i in range(n)]
    a, b = _ols_intercept_slope(xs, zs)
    yhat = [_inv_logit_pct(a + b * xi) for xi in xs]
    coef = {
        "intercepto_logit": round(a, 4),
        "pendiente_logit_mes": round(b, 4),
        **_metricas_ajuste(pcts, yhat, 2),
        "nota": "Logit-lineal sobre % mensual; proyección vía función logística inversa.",
    }
    return yhat, [a, b], coef


def _clamp_pct(y: float) -> float:
    return max(0.0, min(100.0, y))


def _metodo_proporcion(modelo: ModeloProp) -> str:
    if modelo == "estacional":
        return (
            "Regresión del % mensual con tendencia temporal y dummies de mes calendario "
            "(enero referencia); opcional efecto por año si hay historia suficiente. "
            "Recomendado frente a OLS o logit cuando el % oscila mes a mes."
        )
    if modelo == "logistica":
        return (
            "Regresión OLS sobre logit(p/100) del % mensual; la proyección vuelve a escala % "
            "con la función logística inversa. Útil si se espera tendencia suave acotada entre 0 y 100."
        )
    return (
        "Regresión lineal del % mensual frente al índice de mes 0…n−1 en el periodo de ajuste; "
        "extrapolación lineal de la tendencia. No captura estacionalidad ni picos aislados."
    )


def _leyenda_grafico_proporcion() -> str:
    return (
        "Línea azul (% observado): proporción real víctimas fatales / víctimas del mes. "
        "Línea roja (ajuste / proyección): valor del modelo en meses usados para el ajuste, "
        "continuación hasta el fin del rango y meses futuros según el horizonte de predicciones. "
        "No interpretar un pico puntual (p. ej. 2020) como nueva tendencia permanente."
    )


def _interpretacion_bondad_proporcion(
    r2: float,
    mape: float | None,
    modelo: ModeloProp,
) -> dict[str, str]:
    out = _interpretacion_bondad(r2, mape)
    texto = out["interpretacion_bondad"]
    if modelo == "estacional":
        texto += (
            " En P07 el modelo estacional es el de referencia: R² alrededor de 0,35–0,45 "
            "suele ser adecuado para leer meses relativamente altos o bajos en gravedad."
        )
    elif modelo == "logistica":
        texto += (
            " En % fatales muy volátil, logit-lineal suele verse como línea casi plana y R² "
            "cercano a cero; no indica error del sistema sino poca tendencia estable."
        )
    else:
        texto += (
            " OLS sobre % fatales casi siempre deja R² muy bajo (línea plana ~nivel medio); "
            "use estacional para la sustentación si necesita explicar variación mensual."
        )
    out["interpretacion_bondad"] = texto
    return out


def _aplicar_meta_interpretacion(
    meta: dict[str, Any],
    modelo: ModeloProp,
    coeficientes: dict[str, Any] | None,
    sin_modelo: bool,
) -> None:
    meta["metodo"] = _metodo_proporcion(modelo)
    meta["leyenda_grafico"] = _leyenda_grafico_proporcion()
    meta["modelo_recomendado"] = "estacional"
    meta["umbrales_r2_p07"] = {
        "bueno": "≥ 0,55 — ajuste consistente del % en el periodo",
        "moderado": "0,35 – 0,54 — habitual; sirve para patrón mensual, no cifra exacta",
        "bajo": "< 0,35 — revise estacional, periodo más largo o excluir COVID del ajuste",
    }
    if sin_modelo:
        meta["bondad_nivel"] = "bajo"
        meta["interpretacion_bondad"] = (
            f"No hay al menos {_min_meses_modelo('estacional')} meses con ≥ {MIN_VICTIMAS_MES} víctimas "
            "para ajustar. Amplíe fechas o reduzca filtros territoriales."
        )
        return
    if coeficientes:
        bondad = _interpretacion_bondad_proporcion(
            float(coeficientes.get("r2") or 0),
            coeficientes.get("mape_pct"),
            modelo,
        )
        coeficientes.update(bondad)
        meta["interpretacion_bondad"] = bondad["interpretacion_bondad"]
        meta["bondad_nivel"] = bondad["bondad_nivel"]


def _forecast_proporcion(
    modelo: ModeloProp,
    meses_fit: list[str],
    pcts_fit: list[float],
    beta: list[float],
    yhat: list[float],
    horizonte: int,
) -> list[float]:
    """Proyección de % en [0, 100]; estacional con fallback OLS si beta corto."""
    n = len(meses_fit)
    fore: list[float] = []
    mk = meses_fit[-1]
    ctx = _design_ctx_from_meses(meses_fit) if modelo == "estacional" else None
    for k in range(horizonte):
        mk = _next_month_clave(mk)
        if modelo == "estacional" and len(beta) >= 13 and ctx is not None:
            mo = _month_index(mk)
            row = _design_forecast_row(n + k, mo, _year_from_ym(mk), ctx)
            y = sum(b * xv for b, xv in zip(beta, row))
        elif len(beta) >= 2:
            y = beta[0] + beta[1] * float(n + k)
        else:
            y = yhat[-1] if yhat else (pcts_fit[-1] if pcts_fit else 0.0)
        fore.append(round(_clamp_pct(y), 2))
    return fore


def _puente_ajuste_hasta_fin_rango(
    serie_historica: list[dict[str, Any]],
    meses_fit: list[str],
    yhat: list[float],
) -> None:
    """Continúa el ajuste hasta el último mes del rango (meses sin ajuste por COVID/volumen)."""
    if not serie_historica or not yhat or not meses_fit:
        return
    ultimo_ajuste = round(_clamp_pct(yhat[-1]), 2)
    ultimo_fit = meses_fit[-1]
    pasando_ultimo_fit = False
    for row in serie_historica:
        if row["mes_clave"] == ultimo_fit:
            pasando_ultimo_fit = True
            continue
        if pasando_ultimo_fit and row.get("ajuste_pct") is None:
            row["ajuste_pct"] = ultimo_ajuste


def _forecast_logistica(beta: list[float], serie_meses: list[str], horizonte: int) -> list[float]:
    n = len(serie_meses)
    fore: list[float] = []
    mk = serie_meses[-1]
    for k in range(horizonte):
        mk = _next_month_clave(mk)
        t = float(n + k)
        fore.append(round(max(0.0, min(100.0, _inv_logit_pct(beta[0] + beta[1] * t))), 2))
    return fore


def _build_proporcion_single(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
    horizonte_meses: int,
    modelo: ModeloProp,
    excluir_covid: bool,
    comuna_id: int | None,
    comuna_nombre: str | None,
) -> dict[str, Any]:
    hm = max(1, min(12, int(horizonte_meses)))
    meses_all = _iter_meses_clave(inicio, fin)
    excl = MESES_EXCLUIR_COVID_MEDE if excluir_covid else frozenset()
    raw = _query_victimas_fatales_mes(inicio, fin, filtros, comuna_id)

    meses_fit: list[str] = []
    pcts_fit: list[float] = []
    victimas_fit: list[int] = []
    fatales_fit: list[int] = []

    serie_historica: list[dict[str, Any]] = []
    for mk in meses_all:
        d = raw.get(mk, {"victimas": 0, "fatales": 0})
        pct = _pct_fatales(d["victimas"], d["fatales"])
        row: dict[str, Any] = {
            "mes_clave": mk,
            "mes_etiqueta": _etiqueta_mes_ym(mk),
            "victimas": d["victimas"],
            "fatales": d["fatales"],
            "pct_fatales": round(pct, 2) if pct is not None else None,
            "ajuste_pct": None,
        }
        if mk not in excl and pct is not None:
            meses_fit.append(mk)
            pcts_fit.append(pct)
            victimas_fit.append(d["victimas"])
            fatales_fit.append(d["fatales"])
        serie_historica.append(row)

    min_req = _min_meses_modelo("estacional" if modelo == "estacional" else "ols")
    sin_modelo = len(meses_fit) < min_req
    proyeccion: list[dict[str, Any]] = []
    coeficientes: dict[str, Any] | None = None

    if not sin_modelo:
        if modelo == "logistica":
            yhat, beta, coeficientes = _fit_logistica_lineal(meses_fit, pcts_fit)
        elif modelo == "estacional":
            serie = _SerieMensual(meses=meses_fit, valores=[int(round(p)) for p in pcts_fit])
            yhat, beta, coeficientes = _fit_estacional(serie)
            coeficientes["nota"] = "Estacional sobre % fatales (escala 0–100)."
        else:
            xs = [float(i) for i in range(len(pcts_fit))]
            a, b = _ols_intercept_slope(xs, pcts_fit)
            yhat = [_clamp_pct(a + b * xi) for xi in xs]
            beta = [a, b]
            coeficientes = {
                "intercepto_a": round(a, 4),
                "pendiente_b_mes": round(b, 4),
                **_metricas_ajuste(pcts_fit, yhat, 2),
            }

        yhat = [_clamp_pct(v) for v in yhat]
        yhat_by_mes = {mk: round(yhat[i], 2) for i, mk in enumerate(meses_fit)}
        for row in serie_historica:
            if row["mes_clave"] in yhat_by_mes:
                row["ajuste_pct"] = yhat_by_mes[row["mes_clave"]]

        _puente_ajuste_hasta_fin_rango(serie_historica, meses_fit, yhat)

        if modelo == "logistica":
            fore_vals = _forecast_logistica(beta, meses_fit, hm)
        else:
            fore_vals = _forecast_proporcion(modelo, meses_fit, pcts_fit, beta, yhat, hm)

        ultimo_ajuste_rango = serie_historica[-1].get("ajuste_pct") if serie_historica else None
        mk = meses_all[-1]
        for i, fv in enumerate(fore_vals):
            mk = _next_month_clave(mk)
            pct_proj = round(_clamp_pct(fv), 2)
            if i == 0 and ultimo_ajuste_rango is not None:
                pct_proj = round(_clamp_pct(fv if fv > 0 else ultimo_ajuste_rango), 2)
            proyeccion.append(
                {
                    "mes_clave": mk,
                    "mes_etiqueta": _etiqueta_mes_ym(mk),
                    "pct_fatales_proyectado": pct_proj,
                    "ajuste_pct": pct_proj,
                }
            )

    meta: dict[str, Any] = {
        "modelo": modelo,
        "sin_modelo": sin_modelo,
        "min_victimas_mes": MIN_VICTIMAS_MES,
        "excluir_covid_ajuste": excluir_covid,
        "coeficientes": coeficientes,
        "limitaciones": (
            "Indicador ilustrativo (P07): no es riesgo individual ni pronóstico clínico. "
            f"Meses con < {MIN_VICTIMAS_MES} víctimas aparecen en el gráfico pero no entran al ajuste. "
            "R² en OLS/logit suele ser muy bajo; el estacional es el modelo recomendado."
        ),
    }
    _aplicar_meta_interpretacion(meta, modelo, coeficientes, sin_modelo)
    if comuna_id is not None:
        meta["comuna_id"] = comuna_id
        meta["comuna_nombre"] = comuna_nombre

    return {
        "meta": meta,
        "serie_historica": serie_historica,
        "proyeccion": proyeccion,
    }


def build_proporcion_fatales_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
    horizonte_meses: int = 3,
    modelo: str = "estacional",
    excluir_covid: bool = True,
    desglose_comuna: bool = False,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    mod: ModeloProp = (
        modelo if modelo in ("ols", "logistica", "estacional") else "estacional"
    )

    if desglose_comuna and filtros.comuna_id is None:
        from .prioridad_territorial import _query_totales_territorio

        totales = _query_totales_territorio(inicio, fin, filtros, "comuna")
        series: list[dict[str, Any]] = []
        for tid, t in sorted(totales.items(), key=lambda x: -x[1]["incidentes"])[:10]:
            bloque = _build_proporcion_single(
                inicio, fin, filtros, horizonte_meses, mod, excluir_covid, tid, t["nombre"]
            )
            series.append(
                {
                    "comuna_id": tid,
                    "comuna_nombre": t["nombre"],
                    **bloque,
                }
            )
        return {
            "meta": {
                "fecha_inicio": inicio.isoformat(),
                "fecha_fin": fin.isoformat(),
                "horizonte_meses": max(1, min(12, int(horizonte_meses))),
                "modelo": mod,
                "desglose_comuna": True,
                "n_comunas": len(series),
            },
            "series_por_comuna": series,
            "serie_historica": [],
            "proyeccion": [],
        }

    bloque = _build_proporcion_single(
        inicio, fin, filtros, horizonte_meses, mod, excluir_covid, None, None
    )
    bloque["meta"] = {
        "fecha_inicio": inicio.isoformat(),
        "fecha_fin": fin.isoformat(),
        "horizonte_meses": max(1, min(12, int(horizonte_meses))),
        "modelo": mod,
        "desglose_comuna": False,
        **bloque["meta"],
        "filtros": {
            "comuna_id": filtros.comuna_id,
            "barrio_id": filtros.barrio_id,
            "clase_incidente_id": filtros.clase_incidente_id,
        },
    }
    return bloque
