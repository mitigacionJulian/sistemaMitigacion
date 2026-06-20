"""
Proyección descriptiva mensual (Fase A: P02–P04, P06).

Modelos: OLS lineal (P01), tendencia + estacionalidad por mes calendario (P02),
Poisson log-lineal (P04), media móvil simple (P05), criterio μ±3σ (media + bandas). Variables: incidentes, víctimas,
víctimas fatales (P03).
Desglose opcional por clase de incidente (P06).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from django.db import connection

from .evolucion_mensual import _etiqueta_mes_ym, _iter_meses_clave
from .estadistica_series import (
    mape_pct as _mape_pct,
    ols_intercept_slope as _ols_intercept_slope,
    rmse as _rmse,
    r_squared as _r_squared,
    sample_mean,
    sample_std,
    solve_design_ols as _solve_design_ols,
    solve_weighted_least_squares as _normal_equations_solve,
)
from .kpis import FiltrosKpi, _fatal_sql_expr
from .territorio_sql import (
    append_filtros_territoriales,
    meta_filtros_dict,
    nota_modo_territorio,
    punto_critico_serie_sql,
)

ModeloPred = Literal[
    "ols", "estacional", "poisson", "media_movil", "arima", "sarima", "tres_sigma"
]
VariablePred = Literal["incidentes", "victimas", "victimas_fatales"]

MA_VENTANA_DEFAULT = 3
MA_VENTANA_MIN = 2
MA_VENTANA_MAX = 12

HOLDOUT_MESES_DEFAULT = 3
HOLDOUT_MESES_MIN = 1
HOLDOUT_MESES_MAX = 6


@dataclass(frozen=True)
class ArimaOpciones:
    order: tuple[int, int, int] | None = None
    seasonal_order: tuple[int, int, int, int] | None = None


def parse_arima_opciones(qs) -> ArimaOpciones:
    from .modelos_arima import parse_arima_order, parse_sarima_seasonal

    raw_order = qs.get("arima_order")
    raw_seasonal = qs.get("sarima_seasonal")
    order = parse_arima_order(raw_order) if raw_order not in (None, "") else None
    seasonal = parse_sarima_seasonal(raw_seasonal) if raw_seasonal not in (None, "") else None
    if raw_order not in (None, "") and order is None:
        raise ValueError("arima_order")
    if raw_seasonal not in (None, "") and seasonal is None:
        raise ValueError("sarima_seasonal")
    return ArimaOpciones(order=order, seasonal_order=seasonal)


MODELOS_PROYECCION_CARGA = frozenset(
    {"ols", "estacional", "media_movil", "arima", "sarima", "tres_sigma"}
)


def normalize_modelo_proyeccion(modelo: str, default: ModeloPred = "estacional") -> ModeloPred:
    raw = (modelo or default).strip().lower()
    aliases: dict[str, ModeloPred] = {
        "ols": "ols",
        "lineal": "ols",
        "estacional": "estacional",
        "seasonal": "estacional",
        "media_movil": "media_movil",
        "ma": "media_movil",
        "moving_average": "media_movil",
        "arima": "arima",
        "sarima": "sarima",
        "seasonal_arima": "sarima",
        "tres_sigma": "tres_sigma",
        "3_sigma": "tres_sigma",
        "3sigma": "tres_sigma",
        "tres_desviaciones": "tres_sigma",
        "media_3sigma": "tres_sigma",
    }
    if raw in aliases:
        return aliases[raw]
    if raw in MODELOS_PROYECCION_CARGA:
        return raw  # type: ignore[return-value]
    return default

VARIABLE_LABELS = {
    "incidentes": "Incidentes",
    "victimas": "Víctimas",
    "victimas_fatales": "Víctimas fatales",
}

MAX_CLASES_DESGLOSE = 15

# Meses atípicos por confinamiento (Mede): se pueden excluir solo del ajuste, no del gráfico.
MESES_EXCLUIR_COVID_MEDE: frozenset[str] = frozenset(
    {"2020-03", "2020-04", "2020-05", "2020-06", "2020-07", "2020-08"}
)

BETA_POISSON_MAX = 15.0


@dataclass(frozen=True)
class _SerieMensual:
    meses: list[str]
    valores: list[int]


def _parse_ym(ym: str) -> tuple[int, int]:
    y, m = map(int, ym.split("-"))
    return y, m


def _month_index(ym: str) -> int:
    return _parse_ym(ym)[1]


def _next_month_clave(ym: str) -> str:
    y, mo = _parse_ym(ym)
    if mo == 12:
        return f"{y + 1:04d}-01"
    return f"{y:04d}-{mo + 1:02d}"


def _query_mensual_valores(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
    variable: VariablePred,
) -> dict[str, int]:
    filtros = filtros or FiltrosKpi()
    fatal = _fatal_sql_expr("gv")

    where = ["i.fecha_incidente >= %s", "i.fecha_incidente <= %s"]
    params: list[Any] = [inicio, fin]

    append_filtros_territoriales(where, params, filtros)
    if filtros.via_id is not None:
        where.append("i.via_id = %s")
        params.append(filtros.via_id)

    join_sql, join_params, pc_where, pc_params = punto_critico_serie_sql(filtros)
    where.extend(pc_where)
    params.extend(pc_params)

    if variable == "incidentes":
        valor_sql = "COUNT(DISTINCT i.id)::bigint"
    elif variable == "victimas":
        valor_sql = "COUNT(v.id)::bigint"
    else:
        valor_sql = f"COALESCE(SUM(CASE WHEN {fatal} THEN 1 ELSE 0 END), 0)::bigint"

    wh = " AND ".join(where)
    sql = f"""
    SELECT
      to_char(i.fecha_incidente, 'YYYY-MM') AS mes,
      {valor_sql} AS valor
    FROM incidente i
    {join_sql}
    LEFT JOIN victima v ON v.incidente_id = i.id
    LEFT JOIN gravedad_victima gv ON v.gravedad_victima_id = gv.id
    WHERE {wh}
    GROUP BY to_char(i.fecha_incidente, 'YYYY-MM')
    ORDER BY mes
    """
    out: dict[str, int] = {}
    with connection.cursor() as cursor:
        cursor.execute(sql, join_params + params)
        for row in cursor.fetchall():
            out[str(row[0])] = int(row[1] or 0)
    return out


def _query_clases_con_datos(inicio: date, fin: date, filtros: FiltrosKpi) -> list[tuple[int, str, int]]:
    """(clase_id, nombre, total incidentes en rango) ordenado por volumen desc."""
    filtros = filtros or FiltrosKpi()
    where = ["i.fecha_incidente >= %s", "i.fecha_incidente <= %s", "i.clase_incidente_id IS NOT NULL"]
    params: list[Any] = [inicio, fin]
    append_filtros_territoriales(where, params, filtros)
    wh = " AND ".join(where)
    sql = f"""
    SELECT i.clase_incidente_id, COALESCE(ci.nombre, 'Sin clase') AS nombre,
           COUNT(DISTINCT i.id)::bigint AS total
    FROM incidente i
    LEFT JOIN clase_incidente ci ON ci.id = i.clase_incidente_id
    WHERE {wh}
    GROUP BY i.clase_incidente_id, ci.nombre
    ORDER BY total DESC
    LIMIT %s
    """
    params.append(MAX_CLASES_DESGLOSE)
    rows: list[tuple[int, str, int]] = []
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        for row in cursor.fetchall():
            rows.append((int(row[0]), str(row[1] or ""), int(row[2] or 0)))
    return rows


def _interpretacion_bondad(r2: float, mape: float | None) -> dict[str, str]:
    """Texto corto según umbrales de R² (series mensuales de conteo)."""
    if r2 >= 0.55:
        nivel = "bueno"
        texto = (
            "Buen ajuste: el modelo sigue de forma consistente la serie en el periodo y filtros elegidos."
        )
    elif r2 >= 0.35:
        nivel = "moderado"
        texto = (
            "Ajuste moderado: sirve para ver tendencia y orden de magnitud, no para cifras exactas mes a mes."
        )
    else:
        nivel = "bajo"
        texto = (
            "Ajuste bajo en el historial: pruebe estacional, media móvil o active «Excluir mar–ago 2020». "
            "Revise también la prueba con meses reservados (puede ser mejor que el R² sugiere)."
        )

    if mape is not None:
        if mape <= 12:
            texto += f" Error medio aceptable: {mape:g} %."
        elif mape <= 20:
            texto += f" Error medio moderado: {mape:g} %."
        else:
            texto += f" Error medio elevado ({mape:g} %): esta serie es difícil de resumir con este modelo."

    return {"bondad_nivel": nivel, "interpretacion_bondad": texto}


def _metricas_ajuste(ys: list[float], yhat: list[float], n_params: int) -> dict[str, Any]:
    mape = _mape_pct(ys, yhat)
    r2 = round(_r_squared(ys, yhat), 4)
    out: dict[str, Any] = {
        "r2": r2,
        "rmse": round(_rmse(ys, yhat), 2),
        "n_params": n_params,
        "n_obs": len(ys),
        **_interpretacion_bondad(r2, round(mape, 2) if mape is not None else None),
    }
    if mape is not None:
        out["mape_pct"] = round(mape, 2)
    return out


def _year_from_ym(ym: str) -> int:
    return _parse_ym(ym)[0]


def _design_ctx_from_meses(meses: list[str]) -> dict[str, Any]:
    years = sorted({_year_from_ym(m) for m in meses})
    use_year = len(years) >= 2 and len(meses) >= 18
    return {
        "use_year": use_year,
        "years": years,
        "ref_year": years[0] if years else 0,
        "n_params": 2 + 11 + (len(years) - 1 if use_year else 0),
    }


def _design_matrix(meses: list[str]) -> tuple[list[list[float]], dict[str, Any]]:
    """Intercepto, tendencia t, dummies mes 2..12 (enero ref.), opcional dummies año."""
    ctx = _design_ctx_from_meses(meses)
    rows: list[list[float]] = []
    for t, mk in enumerate(meses):
        mo = _month_index(mk)
        yr = _year_from_ym(mk)
        row = [1.0, float(t)]
        for m in range(2, 13):
            row.append(1.0 if mo == m else 0.0)
        if ctx["use_year"]:
            for y in ctx["years"][1:]:
                row.append(1.0 if yr == y else 0.0)
        rows.append(row)
    return rows, ctx


def _design_forecast_row(t_index: int, month: int, year: int, ctx: dict[str, Any]) -> list[float]:
    row = [1.0, float(t_index)]
    for m in range(2, 13):
        row.append(1.0 if month == m else 0.0)
    if ctx.get("use_year"):
        for y in ctx["years"][1:]:
            row.append(1.0 if year == y else 0.0)
    return row


def _predict_linear(beta: list[float], row: list[float]) -> float:
    return max(0.0, sum(b * xv for b, xv in zip(beta, row)))


def _mat_vec_mul(a: list[list[float]], x: list[float]) -> list[float]:
    return [sum(ai * xj for ai, xj in zip(row, x)) for row in a]


def _clamp_beta(beta: list[float]) -> list[float]:
    return [min(BETA_POISSON_MAX, max(-BETA_POISSON_MAX, b)) for b in beta]


def _poisson_predict_row(beta: list[float], row: list[float]) -> float:
    eta = sum(b * xv for b, xv in zip(beta, row))
    eta = min(20.0, max(-20.0, eta))
    return max(0.0, math.exp(eta))


def _fit_estacional(serie: _SerieMensual) -> tuple[list[float], list[float], dict[str, Any]]:
    n = len(serie.meses)
    ys = [float(v) for v in serie.valores]
    x, ctx = _design_matrix(serie.meses)
    beta = _solve_design_ols(x, ys)
    if beta is None:
        a, b = _ols_intercept_slope([float(i) for i in range(n)], ys)
        yhat = [max(0.0, a + b * xi) for xi in range(n)]
        return yhat, [a, b], {"fallback_ols": True, **_metricas_ajuste(ys, yhat, 2)}

    yhat = [_predict_linear(beta, row) for row in x]
    efectos: dict[str, float] = {"1": 0.0}
    for m in range(2, 13):
        efectos[str(m)] = round(beta[1 + (m - 1)], 4)
    efectos_anio: dict[str, float] = {}
    if ctx["use_year"]:
        for i, y in enumerate(ctx["years"][1:], start=13):
            efectos_anio[str(y)] = round(beta[i], 4)
    coef = {
        "intercepto": round(beta[0], 4),
        "pendiente_t_mes": round(beta[1], 4),
        "efectos_mes_calendario": efectos,
        "referencia_mes": "enero",
        "incluye_efecto_anual": ctx["use_year"],
        "referencia_anio": ctx["ref_year"],
        "efectos_anio": efectos_anio if efectos_anio else None,
        **_metricas_ajuste(ys, yhat, ctx["n_params"]),
    }
    return yhat, beta, coef


def _clamp_ventana_ma(ventana: int) -> int:
    return max(MA_VENTANA_MIN, min(MA_VENTANA_MAX, int(ventana)))


def _fit_estacional_vals(
    meses: list[str],
    valores: list[float],
) -> tuple[list[float], list[float], dict[str, Any]]:
    """Estacional sobre valores en escala real (p. ej. % 0–100 con decimales)."""
    serie = _SerieMensual(meses=meses, valores=valores)  # type: ignore[arg-type]
    return _fit_estacional(serie)


def _fit_media_movil_vals(
    meses: list[str],
    valores: list[float],
    ventana: int,
) -> tuple[list[float], list[float], dict[str, Any]]:
    serie = _SerieMensual(meses=meses, valores=valores)  # type: ignore[arg-type]
    return _fit_media_movil(serie, ventana)


def _fit_media_movil(
    serie: _SerieMensual,
    ventana: int,
) -> tuple[list[float], list[float], dict[str, Any]]:
    """Media móvil simple trailing: promedio de los últimos k meses (incluye el mes actual)."""
    k = _clamp_ventana_ma(ventana)
    ys = [float(v) for v in serie.valores]
    n = len(ys)
    yhat: list[float] = []
    for i in range(n):
        start = max(0, i - k + 1)
        window = ys[start : i + 1]
        yhat.append(sum(window) / len(window))
    tail = ys[-k:] if n >= k else ys
    last_ma = sum(tail) / len(tail) if tail else 0.0
    coef = {
        "ventana_meses": k,
        "ultima_media_movil": round(last_ma, 4),
        "metodo_ventana": "media_simple_trailing",
        **_metricas_ajuste(ys, yhat, 1),
    }
    return yhat, [last_ma, float(k)], coef


def _fit_tres_sigma(serie: _SerieMensual) -> tuple[list[float], list[float], dict[str, Any]]:
    """
    Criterio μ±3σ: proyección = media del periodo de ajuste;
    bandas de control en ±3 desviaciones estándar muestrales.
    """
    ys = [float(v) for v in serie.valores]
    n = len(ys)
    media = sample_mean(ys)
    desv = sample_std(ys)
    lim_inf = max(0.0, media - 3.0 * desv)
    lim_sup = media + 3.0 * desv
    yhat = [media] * n
    dentro = sum(1 for y in ys if lim_inf <= y <= lim_sup)
    pct_dentro = round(100.0 * dentro / n, 2) if n else 0.0
    if pct_dentro >= 95:
        nivel = "bueno"
    elif pct_dentro >= 85:
        nivel = "moderado"
    else:
        nivel = "bajo"
    texto = (
        f"Media histórica {media:.1f}; desviación estándar {desv:.1f}. "
        f"{dentro} de {n} meses ({pct_dentro:g} %) caen dentro de μ±3σ "
        f"[{lim_inf:.1f}, {lim_sup:.1f}]. Los meses fuera del intervalo son atípicos "
        "respecto al periodo de ajuste."
    )
    coef = {
        "media_historica": round(media, 4),
        "desviacion_estandar": round(desv, 4),
        "limite_inferior_3sigma": round(lim_inf, 2),
        "limite_superior_3sigma": round(lim_sup, 2),
        "meses_dentro_3sigma": dentro,
        "meses_fuera_3sigma": n - dentro,
        "pct_meses_dentro_3sigma": pct_dentro,
        "nota": (
            "Proyección constante = media del ajuste; bandas μ±3σ delimitan variación "
            "estadística habitual (~99,7 % bajo normalidad)."
        ),
        **_metricas_ajuste(ys, yhat, 2),
        "bondad_nivel": nivel,
        "interpretacion_bondad": texto,
    }
    return yhat, [media, desv], coef


def _fit_poisson(serie: _SerieMensual) -> tuple[list[float], list[float], dict[str, Any]]:
    """Poisson log-lineal: IRLS (mínimos cuadrados ponderados iterados), estable para conteos."""
    n = len(serie.meses)
    ys = [float(v) for v in serie.valores]
    x, ctx = _design_matrix(serie.meses)
    p = len(x[0])
    ymean = max(sum(ys) / max(n, 1), 1.0)
    beta = [math.log(ymean)] + [0.0] * (p - 1)

    for _ in range(35):
        eta: list[float] = []
        mu: list[float] = []
        for k in range(n):
            e = _mat_vec_mul([x[k]], beta)[0]
            e = min(20.0, max(-20.0, e))
            eta.append(e)
            mu.append(math.exp(e))
        z = [eta[k] + (ys[k] - mu[k]) / max(mu[k], 1e-6) for k in range(n)]
        w = [max(mu[k], 1e-6) for k in range(n)]
        new_beta = _normal_equations_solve(x, z, w)
        if new_beta is None:
            break
        new_beta = _clamp_beta(new_beta)
        if max(abs(new_beta[j] - beta[j]) for j in range(p)) < 1e-5:
            beta = new_beta
            break
        beta = new_beta

    yhat = [_poisson_predict_row(beta, x[k]) for k in range(n)]
    y_max = max(ys) if ys else 0.0
    unstable = (
        not yhat
        or max(yhat) > max(y_max * 4, 5000)
        or any(math.isinf(v) or math.isnan(v) for v in yhat)
        or abs(beta[1]) > 5.0
    )

    if unstable:
        yhat, beta, coef_lin = _fit_estacional(serie)
        coef = {
            **{k: v for k, v in coef_lin.items() if k != "referencia_mes"},
            "fallback_estacional": True,
            "r2_pseudo": coef_lin.get("r2"),
            "nota": (
                "Poisson no convergió de forma estable; se muestra el ajuste estacional equivalente "
                "para la línea del gráfico."
            ),
        }
        return yhat, beta, coef

    b1 = beta[1]
    factor = math.exp(min(5.0, max(-5.0, b1)))
    coef = {
        "intercepto_log": round(beta[0], 4),
        "pendiente_t_log": round(b1, 4),
        "factor_tendencia_mensual": round(factor, 4),
        "cambio_tendencia_pct_aprox": round((factor - 1.0) * 100.0, 2),
        **_metricas_ajuste(ys, yhat, ctx["n_params"]),
        "r2_pseudo": round(_r_squared(ys, yhat), 4),
        "incluye_efecto_anual": ctx["use_year"],
        "nota": (
            "exp(pendiente_t_log) ≈ factor multiplicativo de la tendencia por mes "
            "(manteniendo fijos intercepto y estacionalidad)."
        ),
    }
    return yhat, beta, coef


def _forecast_values(
    modelo: ModeloPred,
    serie: _SerieMensual,
    beta: list[float],
    horizonte: int,
    yhat_hist: list[float],
) -> list[float]:
    n = len(serie.meses)
    fore: list[float] = []
    mk = serie.meses[-1]
    for k in range(horizonte):
        mk = _next_month_clave(mk)
        mo = _month_index(mk)
        t_idx = float(n + k)
        if modelo == "ols" and len(beta) >= 2:
            y = max(0.0, beta[0] + beta[1] * t_idx)
        elif modelo in ("estacional", "poisson") and len(beta) >= 13:
            ctx = _design_ctx_from_meses(serie.meses)
            row = _design_forecast_row(int(t_idx), mo, _year_from_ym(mk), ctx)
            if modelo == "poisson":
                y = _poisson_predict_row(beta, row)
            else:
                y = sum(b * xv for b, xv in zip(beta, row))
            y = max(0.0, y)
        elif modelo == "media_movil" and beta:
            y = max(0.0, beta[0])
        elif modelo == "tres_sigma" and beta:
            y = max(0.0, beta[0])
        else:
            y = yhat_hist[-1] if yhat_hist else 0.0
        fore.append(round(y, 2))
    return fore


def _clamp_holdout_meses(holdout: int) -> int:
    return max(HOLDOUT_MESES_MIN, min(HOLDOUT_MESES_MAX, int(holdout)))


def _forecast_from_train(
    meses_train: list[str],
    valores_train: list[float],
    modelo: ModeloPred,
    horizonte: int,
    ventana_ma: int,
    arima_opciones: ArimaOpciones | None = None,
) -> list[float] | None:
    """Ajusta solo con entrenamiento y proyecta `horizonte` meses hacia adelante."""
    n = len(meses_train)
    if n < 1 or horizonte < 1:
        return None
    serie = _SerieMensual(meses=meses_train, valores=[int(v) for v in valores_train])
    ys = [float(v) for v in valores_train]
    ventana = _clamp_ventana_ma(ventana_ma)
    hm = max(1, int(horizonte))

    if modelo == "ols":
        xs = [float(i) for i in range(n)]
        a, b = _ols_intercept_slope(xs, ys)
        beta = [a, b]
        yhat_hist = [max(0.0, a + b * xi) for xi in xs]
        return _forecast_values("ols", serie, beta, hm, yhat_hist)
    if modelo == "estacional":
        yhat, beta, _ = _fit_estacional(serie)
        return _forecast_values("estacional", serie, beta, hm, yhat)
    if modelo == "media_movil":
        yhat, beta, _ = _fit_media_movil(serie, ventana)
        return _forecast_values("media_movil", serie, beta, hm, yhat)
    if modelo == "tres_sigma":
        yhat, beta, _ = _fit_tres_sigma(serie)
        return _forecast_values("tres_sigma", serie, beta, hm, yhat)
    if modelo in ("arima", "sarima"):
        from .modelos_arima import ajustar_y_proyectar_arima

        opts = arima_opciones or ArimaOpciones()
        res = ajustar_y_proyectar_arima(
            ys,
            hm,
            seasonal=(modelo == "sarima"),
            order=opts.order,
            seasonal_order=opts.seasonal_order,
        )
        if res is None:
            return None
        _, fore, _ = res
        return fore
    yhat, beta, coef = _fit_poisson(serie)
    modelo_forecast: ModeloPred = modelo
    if coef.get("fallback_estacional"):
        modelo_forecast = "estacional"
    return _forecast_values(modelo_forecast, serie, beta, hm, yhat)


def _interpretacion_holdout(
    mape: float | None,
    mape_in_sample: float | None,
) -> str:
    if mape is None:
        return (
            "Se entrenó sin los últimos meses reservados y se comparó la predicción con lo observado."
        )
    precision = max(0.0, min(100.0, 100.0 - mape))
    texto = (
        f"En la prueba, el error medio fue de {mape:g} % "
        f"(precisión estimada ≈ {precision:g} %)."
    )
    if precision >= 80:
        texto += " Resultado aceptable para usar este modelo como referencia."
    elif precision >= 70:
        texto += " Precisión moderada: conviene comparar con otro modelo o ampliar fechas."
    else:
        texto += " Precisión baja: no es el modelo más adecuado con estos filtros."
    if mape_in_sample is not None:
        diff = mape - mape_in_sample
        if diff > 5:
            texto += (
                f" El error en la prueba supera el del ajuste al historial ({mape_in_sample:g} %): "
                "el modelo puede estar ajustándose demasiado al pasado."
            )
        elif diff <= 2:
            texto += (
                f" Coherente con el ajuste al historial ({mape_in_sample:g} %)."
            )
        else:
            texto += (
                f" Ajuste al historial: MAPE {mape_in_sample:g} %."
            )
    return texto


def _evaluar_holdout(
    meses_fit: list[str],
    valores_fit: list[int],
    modelo: ModeloPred,
    holdout_meses: int,
    ventana_ma: int,
    mape_in_sample: float | None = None,
    arima_opciones: ArimaOpciones | None = None,
) -> dict[str, Any]:
    """
    Reserva los últimos h meses del ajuste como prueba:
    entrena con el resto y compara predicción vs observado.
    """
    h = _clamp_holdout_meses(holdout_meses)
    n = len(meses_fit)
    min_train = _min_meses_modelo(modelo, ventana_ma)
    min_total = min_train + h

    if n < min_total:
        return {
            "activo": False,
            "holdout_meses": h,
            "motivo": (
                f"Se requieren al menos {min_total} meses de ajuste para reservar {h} meses de prueba "
                f"(mínimo del modelo: {min_train})."
            ),
        }

    if modelo == "poisson" and sum(valores_fit[:-h]) == 0:
        return {
            "activo": False,
            "holdout_meses": h,
            "motivo": "Poisson requiere conteos positivos en el tramo de entrenamiento.",
        }

    train_meses = meses_fit[:-h]
    train_vals = [float(v) for v in valores_fit[:-h]]
    test_meses = meses_fit[-h:]
    test_vals = [float(v) for v in valores_fit[-h:]]

    fore = _forecast_from_train(
        train_meses, train_vals, modelo, h, ventana_ma, arima_opciones=arima_opciones
    )
    if fore is None or len(fore) != h:
        return {
            "activo": False,
            "holdout_meses": h,
            "motivo": "No se pudo ajustar o proyectar con el tramo de entrenamiento reservado.",
        }

    metricas = _metricas_ajuste(test_vals, fore, 2)
    filas: list[dict[str, Any]] = []
    for i, mk in enumerate(test_meses):
        obs = test_vals[i]
        pred = fore[i]
        err_pct = round(100.0 * abs(obs - pred) / obs, 2) if obs > 0 else None
        filas.append(
            {
                "mes_clave": mk,
                "mes_etiqueta": _etiqueta_mes_ym(mk),
                "observados": int(obs),
                "predichos": pred,
                "error_abs": round(abs(obs - pred), 2),
                "error_pct": err_pct,
            }
        )

    mape_hold = metricas.get("mape_pct")
    precision_est = (
        round(max(0.0, min(100.0, 100.0 - float(mape_hold))), 2)
        if mape_hold is not None
        else None
    )
    cumple_umbral_80 = precision_est is not None and precision_est >= 80.0
    return {
        "activo": True,
        "holdout_meses": h,
        "n_meses_entrenamiento": len(train_meses),
        "ultimo_mes_entrenamiento": train_meses[-1],
        "primer_mes_prueba": test_meses[0],
        "ultimo_mes_prueba": test_meses[-1],
        "meses_prueba": filas,
        "r2": metricas["r2"],
        "rmse": metricas["rmse"],
        "mape_pct": mape_hold,
        "precision_estimada_pct": precision_est,
        "cumple_umbral_80": cumple_umbral_80,
        "bondad_nivel": metricas.get("bondad_nivel"),
        "interpretacion_holdout": _interpretacion_holdout(
            float(mape_hold) if mape_hold is not None else None,
            mape_in_sample,
        ),
        "metodo": (
            f"Se entrenó con {len(train_meses)} meses (hasta {_etiqueta_mes_ym(train_meses[-1])}) "
            f"y se comparó la predicción con los últimos {h} meses, que no se usaron al entrenar."
        ),
    }


def _row_historica(
    mk: str,
    obs: int,
    ajuste: float | None,
    variable: VariablePred,
    *,
    bandas_3sigma: tuple[float | None, float | None] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "mes_clave": mk,
        "mes_etiqueta": _etiqueta_mes_ym(mk),
        "observados": obs,
        "ajuste_modelo": ajuste,
    }
    if bandas_3sigma is not None:
        lim_inf, lim_sup = bandas_3sigma
        if lim_inf is not None and lim_sup is not None:
            row["banda_inf_3sigma"] = lim_inf
            row["banda_sup_3sigma"] = lim_sup
            row["fuera_3sigma"] = obs < lim_inf or obs > lim_sup
    if variable == "incidentes":
        row["incidentes_observados"] = obs
        row["incidentes_ajuste_lineal"] = ajuste
    return row


def _row_proyeccion(
    mk: str,
    valor: float,
    variable: VariablePred,
    *,
    bandas_3sigma: tuple[float | None, float | None] | None = None,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "mes_clave": mk,
        "mes_etiqueta": _etiqueta_mes_ym(mk),
        "proyectados": valor,
        "ajuste_modelo": valor,
    }
    if bandas_3sigma is not None:
        lim_inf, lim_sup = bandas_3sigma
        if lim_inf is not None and lim_sup is not None:
            row["banda_inf_3sigma"] = lim_inf
            row["banda_sup_3sigma"] = lim_sup
    if variable == "incidentes":
        row["incidentes_proyectados"] = valor
        row["incidentes_ajuste_lineal"] = valor
    return row


def _metodo_texto(modelo: ModeloPred) -> str:
    if modelo == "ols":
        return (
            "Regresión lineal (mínimos cuadrados) sobre el conteo mensual; "
            "eje temporal = índice de mes 0…n−1 en el rango."
        )
    if modelo == "estacional":
        return (
            "Regresión lineal con tendencia (índice de mes), dummies de mes calendario "
            "(enero referencia) y, si hay ≥2 años y ≥18 meses en el ajuste, efectos por año "
            "(primer año referencia)."
        )
    if modelo == "media_movil":
        return (
            "Media móvil simple (ventana k meses): el ajuste histórico es el promedio "
            "de los últimos k meses incluyendo el mes actual; la proyección repite la media "
            "de los k meses más recientes del ajuste."
        )
    if modelo == "tres_sigma":
        return (
            "Criterio de tres desviaciones estándar (μ±3σ): la proyección repite la media "
            "muestral del periodo de ajuste; las bandas delimitan variación habitual "
            "estadística (≈99,7 % bajo normalidad)."
        )
    if modelo == "arima":
        return (
            "ARIMA sobre la serie mensual: modelo autorregresivo integrado de media móvil "
            "(por defecto orden (2,1,3)) estimado por máxima verosimilitud."
        )
    if modelo == "sarima":
        return (
            "SARIMA sobre la serie mensual: ARIMA con componente estacional de periodo 12 meses "
            "(por defecto (2,1,3)(1,1,1,12)); adecuado cuando hay patrón intra-anual repetible."
        )
    return (
        "Modelo de Poisson log-lineal (GLM): tendencia + estacionalidad por mes; "
        "ajuste por scoring iterativo (máx. verosimilitud)."
    )


def _limitaciones_texto(modelo: ModeloPred, variable: VariablePred) -> str:
    base = (
        "Proyección ilustrativa: no incorpora cambios normativos, shocks externos ni variables exógenas; "
        "no sustituye estudios de demanda o modelos de riesgo espacial. Valores proyectados ≥ 0."
    )
    if modelo == "ols":
        return base + " El modelo OLS no captura estacionalidad intra-anual."
    if modelo == "estacional":
        return base + " La estacionalidad asume patrón repetible año a año en el rango disponible."
    if modelo == "media_movil":
        return (
            base
            + " La media móvil no modela tendencia ni estacionalidad; suaviza la serie "
            "y asume persistencia del nivel reciente."
        )
    if modelo == "tres_sigma":
        return (
            base
            + " La proyección constante (media) no captura tendencia ni estacionalidad; "
            "las bandas μ±3σ sirven para identificar meses atípicos, no como intervalo "
            "de confianza formal de la predicción."
        )
    if modelo == "arima":
        return (
            base
            + " ARIMA asume estacionariedad tras diferenciación; requiere al menos 12 meses "
            "en el ajuste y puede sobreajustar series cortas o con shocks."
        )
    if modelo == "sarima":
        return (
            base
            + " SARIMA requiere al menos 24 meses para estimar estacionalidad mensual; "
            "los conteos se tratan como serie real (no enteros) y la proyección se recorta a ≥ 0."
        )
    return base + " Poisson asume varianza≈media; si hay sobredispersión, la incertidumbre puede subestimarse."


def _min_meses_modelo(modelo: ModeloPred, ventana_ma: int = MA_VENTANA_DEFAULT) -> int:
    if modelo == "ols":
        return 2
    if modelo == "tres_sigma":
        return 2
    if modelo == "media_movil":
        return _clamp_ventana_ma(ventana_ma)
    if modelo == "arima":
        from .modelos_arima import MIN_MESES_ARIMA

        return MIN_MESES_ARIMA
    if modelo == "sarima":
        from .modelos_arima import MIN_MESES_SARIMA

        return MIN_MESES_SARIMA
    return 3


def _meses_excluir_ajuste(excluir_covid: bool) -> set[str]:
    return set(MESES_EXCLUIR_COVID_MEDE) if excluir_covid else set()


def _build_single(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
    horizonte_meses: int,
    modelo: ModeloPred,
    variable: VariablePred,
    excluir_covid: bool = False,
    ventana_ma: int = MA_VENTANA_DEFAULT,
    holdout_meses: int = HOLDOUT_MESES_DEFAULT,
    evaluar_holdout: bool = True,
    arima_opciones: ArimaOpciones | None = None,
) -> dict[str, Any]:
    hm = max(1, min(12, int(horizonte_meses)))
    ventana = _clamp_ventana_ma(ventana_ma)
    meses = _iter_meses_clave(inicio, fin)
    raw = _query_mensual_valores(inicio, fin, filtros, variable)
    valores = [raw.get(mk, 0) for mk in meses]
    excl = _meses_excluir_ajuste(excluir_covid)
    meses_fit = [mk for mk in meses if mk not in excl]
    valores_fit = [raw.get(mk, 0) for mk in meses_fit]
    serie_fit = _SerieMensual(meses=meses_fit, valores=valores_fit)
    n_fit = len(meses_fit)
    ys_fit = [float(v) for v in valores_fit]

    sin_modelo = (
        n_fit < _min_meses_modelo(modelo, ventana)
        or (modelo == "poisson" and sum(valores_fit) == 0)
    )
    serie_historica: list[dict[str, Any]] = []
    proyeccion: list[dict[str, Any]] = []
    coeficientes: dict[str, Any] | None = None
    beta: list[float] = []
    yhat_by_mes: dict[str, float] = {}
    fore_direct: list[float] | None = None

    if not sin_modelo:
        if modelo == "ols":
            xs = [float(i) for i in range(n_fit)]
            a, b = _ols_intercept_slope(xs, ys_fit)
            beta = [a, b]
            for i, mk in enumerate(meses_fit):
                yhat_by_mes[mk] = max(0.0, a + b * xs[i])
            yhat_list = list(yhat_by_mes.values())
            coeficientes = {
                "intercepto_a": round(a, 4),
                "pendiente_b_mes": round(b, 4),
                **_metricas_ajuste(ys_fit, yhat_list, 2),
            }
        elif modelo == "estacional":
            yhat_fit, beta, coeficientes = _fit_estacional(serie_fit)
            for i, mk in enumerate(meses_fit):
                yhat_by_mes[mk] = yhat_fit[i]
        elif modelo == "media_movil":
            yhat_fit, beta, coeficientes = _fit_media_movil(serie_fit, ventana)
            for i, mk in enumerate(meses_fit):
                yhat_by_mes[mk] = yhat_fit[i]
        elif modelo == "tres_sigma":
            yhat_fit, beta, coeficientes = _fit_tres_sigma(serie_fit)
            for i, mk in enumerate(meses_fit):
                yhat_by_mes[mk] = yhat_fit[i]
        elif modelo in ("arima", "sarima"):
            from .modelos_arima import ajustar_y_proyectar_arima

            opts = arima_opciones or ArimaOpciones()
            arima_res = ajustar_y_proyectar_arima(
                ys_fit,
                hm,
                seasonal=(modelo == "sarima"),
                order=opts.order,
                seasonal_order=opts.seasonal_order,
            )
            if arima_res is None:
                sin_modelo = True
            else:
                yhat_fit, fore_direct, coeficientes = arima_res
                for i, mk in enumerate(meses_fit):
                    yhat_by_mes[mk] = yhat_fit[i]
        else:
            yhat_fit, beta, coeficientes = _fit_poisson(serie_fit)
            for i, mk in enumerate(meses_fit):
                yhat_by_mes[mk] = yhat_fit[i]

    if not sin_modelo:
        bandas_3sigma: tuple[float | None, float | None] | None = None
        if modelo == "tres_sigma" and coeficientes:
            bandas_3sigma = (
                coeficientes.get("limite_inferior_3sigma"),
                coeficientes.get("limite_superior_3sigma"),
            )
        for i, mk in enumerate(meses):
            ajuste = round(yhat_by_mes[mk], 2) if mk in yhat_by_mes else None
            serie_historica.append(
                _row_historica(mk, valores[i], ajuste, variable, bandas_3sigma=bandas_3sigma)
            )

        if fore_direct is not None:
            fore = fore_direct
        else:
            yhat_hist_list = [yhat_by_mes[mk] for mk in meses_fit]
            modelo_forecast: ModeloPred = modelo
            if modelo == "poisson" and coeficientes and coeficientes.get("fallback_estacional"):
                modelo_forecast = "estacional"
            fore = _forecast_values(modelo_forecast, serie_fit, beta, hm, yhat_hist_list)
        mk = meses[-1]
        for yf in fore:
            mk = _next_month_clave(mk)
            proyeccion.append(
                _row_proyeccion(mk, yf, variable, bandas_3sigma=bandas_3sigma)
            )
    else:
        for i, mk in enumerate(meses):
            serie_historica.append(_row_historica(mk, valores[i], None, variable))

    lim = _limitaciones_texto(modelo, variable)
    if excluir_covid and excl:
        lim += (
            " Meses mar–ago 2020 excluidos del ajuste (confinamiento); siguen visibles como observados."
        )

    meta: dict[str, Any] = {
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "horizonte_meses": hm,
            "modelo": modelo,
            "variable": variable,
            "variable_etiqueta": VARIABLE_LABELS[variable],
            "sin_modelo": sin_modelo,
            "metodo": _metodo_texto(modelo),
            "coeficientes": coeficientes,
            "limitaciones": lim,
            "excluir_covid": excluir_covid,
            "meses_excluidos_ajuste": sorted(excl & set(meses)),
            "n_meses_ajuste": n_fit,
            "filtros": meta_filtros_dict(filtros),
            "nota_territorio": nota_modo_territorio(filtros.modo_territorio),
        }
    if modelo == "media_movil":
        meta["ventana_meses"] = ventana
    if modelo in ("arima", "sarima"):
        opts = arima_opciones or ArimaOpciones()
        from .modelos_arima import ARIMA_ORDER_DEFAULT, SARIMA_SEASONAL_DEFAULT

        meta["arima_order"] = list(opts.order or ARIMA_ORDER_DEFAULT)
        if modelo == "sarima":
            meta["sarima_seasonal"] = list(opts.seasonal_order or SARIMA_SEASONAL_DEFAULT)
    if coeficientes:
        meta["interpretacion_bondad"] = coeficientes.get("interpretacion_bondad")
        meta["bondad_nivel"] = coeficientes.get("bondad_nivel")

    if evaluar_holdout and not sin_modelo:
        mape_in = coeficientes.get("mape_pct") if coeficientes else None
        meta["holdout"] = _evaluar_holdout(
            meses_fit,
            valores_fit,
            modelo,
            holdout_meses,
            ventana,
            mape_in_sample=float(mape_in) if mape_in is not None else None,
            arima_opciones=arima_opciones,
        )
        hold = meta["holdout"]
        if (
            hold.get("activo")
            and coeficientes
            and coeficientes.get("r2") is not None
            and float(coeficientes["r2"]) < 0.35
            and hold.get("mape_pct") is not None
            and float(hold["mape_pct"]) <= 20
        ):
            extra = (
                f" La prueba con meses reservados es aceptable (MAPE {float(hold['mape_pct']):g} %), "
                "aunque el R² del ajuste sea bajo."
            )
            texto_b = coeficientes.get("interpretacion_bondad") or ""
            coeficientes["interpretacion_bondad"] = texto_b + extra
            meta["interpretacion_bondad"] = coeficientes["interpretacion_bondad"]
    elif evaluar_holdout:
        meta["holdout"] = {
            "activo": False,
            "holdout_meses": _clamp_holdout_meses(holdout_meses),
            "motivo": "No hay modelo ajustado para validación hold-out.",
        }

    return {
        "meta": meta,
        "serie_historica": serie_historica,
        "proyeccion": proyeccion,
    }


def build_predicciones_mensuales_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
    horizonte_meses: int = 3,
    modelo: str = "ols",
    variable: str = "incidentes",
    desglose_clase: bool = False,
    excluir_covid: bool = False,
    ventana_ma: int = MA_VENTANA_DEFAULT,
    holdout_meses: int = HOLDOUT_MESES_DEFAULT,
    evaluar_holdout: bool = True,
    arima_opciones: ArimaOpciones | None = None,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    mod: ModeloPred = (
        modelo
        if modelo in ("ols", "estacional", "poisson", "media_movil", "arima", "sarima", "tres_sigma")
        else "ols"
    )
    ventana = _clamp_ventana_ma(ventana_ma)
    holdout = _clamp_holdout_meses(holdout_meses)
    var: VariablePred = (
        variable
        if variable in ("incidentes", "victimas", "victimas_fatales")
        else "incidentes"
    )

    if desglose_clase and filtros.clase_incidente_id is None:
        clases = _query_clases_con_datos(inicio, fin, filtros)
        series_por_clase: list[dict[str, Any]] = []
        for cid, nombre, _total in clases:
            f_clase = FiltrosKpi(
                comuna_id=filtros.comuna_id,
                barrio_id=filtros.barrio_id,
                clase_incidente_id=cid,
                modo_territorio=filtros.modo_territorio,
            )
            bloque = _build_single(
                inicio,
                fin,
                f_clase,
                horizonte_meses,
                mod,
                var,
                excluir_covid=excluir_covid,
                ventana_ma=ventana,
                holdout_meses=holdout,
                evaluar_holdout=evaluar_holdout,
                arima_opciones=arima_opciones,
            )
            series_por_clase.append(
                {
                    "clase_incidente_id": cid,
                    "clase_nombre": nombre,
                    "serie_historica": bloque["serie_historica"],
                    "proyeccion": bloque["proyeccion"],
                    "meta": bloque["meta"],
                }
            )
        return {
            "meta": {
                "fecha_inicio": inicio.isoformat(),
                "fecha_fin": fin.isoformat(),
                "horizonte_meses": max(1, min(12, int(horizonte_meses))),
                "modelo": mod,
                "variable": var,
                "variable_etiqueta": VARIABLE_LABELS[var],
                "desglose_clase": True,
                "n_clases": len(series_por_clase),
                "limitaciones": _limitaciones_texto(mod, var)
                + " Cada serie usa filtro fijo por clase de incidente.",
                "filtros": meta_filtros_dict(filtros),
                "nota_territorio": nota_modo_territorio(filtros.modo_territorio),
            },
            "series_por_clase": series_por_clase,
            "serie_historica": [],
            "proyeccion": [],
        }

    bloque = _build_single(
        inicio,
        fin,
        filtros,
        horizonte_meses,
        mod,
        var,
        excluir_covid=excluir_covid,
        ventana_ma=ventana,
        holdout_meses=holdout,
        evaluar_holdout=evaluar_holdout,
        arima_opciones=arima_opciones,
    )
    bloque["meta"]["desglose_clase"] = False
    return bloque


# Compatibilidad tests que parchean agregación mensual de incidentes
def _query_agregado_por_mes(inicio: date, fin: date, filtros: FiltrosKpi) -> dict[str, tuple[int, int]]:
    raw = _query_mensual_valores(inicio, fin, filtros, "incidentes")
    return {k: (v, 0) for k, v in raw.items()}
