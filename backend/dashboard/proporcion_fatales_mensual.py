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
from .territorio_sql import barrio_fk_col, comuna_fk_col, meta_filtros_dict, nota_modo_territorio
from .predicciones_mensuales import (
    HOLDOUT_MESES_DEFAULT,
    MA_VENTANA_DEFAULT,
    MESES_EXCLUIR_COVID_MEDE,
    ArimaOpciones,
    _SerieMensual,
    _clamp_holdout_meses,
    _clamp_ventana_ma,
    _design_ctx_from_meses,
    _design_forecast_row,
    _design_matrix,
    _fit_estacional_vals,
    _fit_media_movil_vals,
    _forecast_values,
    _interpretacion_bondad,
    _interpretacion_holdout,
    _metricas_ajuste,
    _min_meses_modelo,
    _month_index,
    _next_month_clave,
    _normal_equations_solve,
    _ols_intercept_slope,
    _year_from_ym,
)

ModeloProp = Literal[
    "ols",
    "logistica",
    "estacional",
    "logit_offset",
    "ratio_compuesto",
    "media_movil",
    "arima",
    "sarima",
]
MIN_VICTIMAS_MES = 10
MESES_AJUSTE_RECOMENDADOS = 24
Z_BANDA_CONFIANZA = 1.96


def _where_sql(filtros: FiltrosKpi, comuna_id: int | None) -> tuple[str, list[Any]]:
    where = ["i.fecha_incidente >= %s", "i.fecha_incidente <= %s"]
    params: list[Any] = []
    modo = filtros.modo_territorio or "registro"
    if modo == "espacial":
        where.append("i.ubicacion IS NOT NULL")
    col_c = comuna_fk_col(modo)
    col_b = barrio_fk_col(modo)
    if comuna_id is not None:
        where.append(f"i.{col_c} = %s")
        params.append(comuna_id)
    elif filtros.comuna_id is not None:
        where.append(f"i.{col_c} = %s")
        params.append(filtros.comuna_id)
    if filtros.barrio_id is not None:
        where.append(f"i.{col_b} = %s")
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


def _predict_linear_raw(beta: list[float], row: list[float]) -> float:
    return sum(b * xv for b, xv in zip(beta, row))


def _fit_logit_offset_estacional(
    meses: list[str],
    pcts: list[float],
    victimas: list[int],
) -> tuple[list[float], list[float], dict[str, Any]]:
    """WLS sobre logit(p) ponderado por víctimas del mes (exposición)."""
    zs = [_logit(p) for p in pcts]
    weights = [max(1.0, float(v)) for v in victimas]
    x, _ctx = _design_matrix(meses)
    beta = _normal_equations_solve(x, zs, weights)
    n = len(pcts)
    if beta is None:
        a, b = _ols_intercept_slope([float(i) for i in range(n)], zs)
        yhat = [_clamp_pct(_inv_logit_pct(a + b * xi)) for xi in range(n)]
        return yhat, [a, b], {
            "fallback_ols_logit": True,
            **_metricas_ajuste(pcts, yhat, 2),
            "nota": "Logit con exposición (víctimas/mes como peso).",
        }
    yhat = [_clamp_pct(_inv_logit_pct(_predict_linear_raw(beta, row))) for row in x]
    coef = {
        "intercepto_logit": round(beta[0], 4),
        "pendiente_t_mes": round(beta[1], 4) if len(beta) > 1 else 0.0,
        "ponderacion": "victimas_mes",
        **_metricas_ajuste(pcts, yhat, len(beta)),
        "nota": "Logit con exposición: WLS sobre logit(%) con peso = víctimas del mes.",
    }
    return yhat, beta, coef


def _forecast_logit_offset(
    meses_fit: list[str],
    beta: list[float],
    horizonte: int,
) -> list[float]:
    n = len(meses_fit)
    fore: list[float] = []
    mk = meses_fit[-1]
    ctx = _design_ctx_from_meses(meses_fit)
    for k in range(horizonte):
        mk = _next_month_clave(mk)
        mo = _month_index(mk)
        row = _design_forecast_row(n + k, mo, _year_from_ym(mk), ctx)
        if len(beta) >= 13:
            eta = _predict_linear_raw(beta, row)
        elif len(beta) >= 2:
            eta = beta[0] + beta[1] * float(n + k)
        else:
            eta = beta[0] if beta else 0.0
        fore.append(round(_clamp_pct(_inv_logit_pct(eta)), 2))
    return fore


def _fit_ratio_compuesto(
    meses: list[str],
    victimas: list[int],
    fatales: list[int],
) -> tuple[list[float], list[float], dict[str, Any], list[float], list[float]]:
    yhat_v, beta_v, coef_v = _fit_estacional_vals(meses, [float(v) for v in victimas])
    yhat_f, beta_f, coef_f = _fit_estacional_vals(meses, [float(f) for f in fatales])
    yhat_pct = [_clamp_pct(100.0 * f / max(v, 1.0)) for f, v in zip(yhat_f, yhat_v)]
    beta = beta_f + beta_v
    coef = {
        "modelo_fatales": coef_f,
        "modelo_victimas": coef_v,
        **_metricas_ajuste(
            [100.0 * f / max(v, 1.0) for f, v in zip(fatales, victimas)],
            yhat_pct,
            2,
        ),
        "nota": "Ratio compuesto: estacional sobre fatales y víctimas; % = fatales÷víctimas proyectados.",
    }
    return yhat_pct, beta, coef, yhat_f, yhat_v


def _forecast_ratio_compuesto(
    meses_fit: list[str],
    victimas_fit: list[int],
    fatales_fit: list[int],
    horizonte: int,
) -> list[float]:
    serie_v = _SerieMensual(meses=meses_fit, valores=victimas_fit)
    serie_f = _SerieMensual(meses=meses_fit, valores=fatales_fit)
    yhat_v, beta_v, _ = _fit_estacional_vals(meses_fit, [float(v) for v in victimas_fit])
    yhat_f, beta_f, _ = _fit_estacional_vals(meses_fit, [float(f) for f in fatales_fit])
    fore_v = _forecast_values("estacional", serie_v, beta_v, horizonte, yhat_v)
    fore_f = _forecast_values("estacional", serie_f, beta_f, horizonte, yhat_f)
    return [
        round(_clamp_pct(100.0 * f / max(v, 1.0)), 2)
        for f, v in zip(fore_f, fore_v)
    ]


def _ajustar_proporcion(
    modelo: ModeloProp,
    meses_fit: list[str],
    pcts_fit: list[float],
    victimas_fit: list[int],
    fatales_fit: list[int],
    ventana: int,
    horizonte: int,
    arima_opciones: ArimaOpciones | None,
) -> tuple[list[float], list[float], dict[str, Any], list[float] | None, bool]:
    fore_direct: list[float] | None = None
    if modelo == "logistica":
        yhat, beta, coef = _fit_logistica_lineal(meses_fit, pcts_fit)
    elif modelo == "logit_offset":
        yhat, beta, coef = _fit_logit_offset_estacional(meses_fit, pcts_fit, victimas_fit)
    elif modelo == "ratio_compuesto":
        yhat, beta, coef, _, _ = _fit_ratio_compuesto(meses_fit, victimas_fit, fatales_fit)
    elif modelo == "estacional":
        yhat, beta, coef = _fit_estacional_vals(meses_fit, pcts_fit)
        coef["nota"] = "Estacional sobre % fatales (escala 0–100, sin redondeo)."
    elif modelo == "media_movil":
        yhat, beta, coef = _fit_media_movil_vals(meses_fit, pcts_fit, ventana)
        coef["nota"] = "Media móvil sobre % fatales; proyección al último valor suavizado."
    elif modelo in ("arima", "sarima"):
        from .modelos_arima import ajustar_y_proyectar_arima

        arima_res = ajustar_y_proyectar_arima(
            pcts_fit,
            horizonte,
            seasonal=(modelo == "sarima"),
            valor_min=0.0,
            valor_max=100.0,
            order=(arima_opciones or ArimaOpciones()).order,
            seasonal_order=(arima_opciones or ArimaOpciones()).seasonal_order,
        )
        if arima_res is None:
            return [], [], {}, None, True
        yhat, fore_direct, coef = arima_res
        beta = []
        coef["nota"] = (
            f"{'SARIMA' if modelo == 'sarima' else 'ARIMA'} sobre % fatales (0–100)."
        )
        return yhat, beta, coef, fore_direct, False
    else:
        xs = [float(i) for i in range(len(pcts_fit))]
        a, b = _ols_intercept_slope(xs, pcts_fit)
        yhat = [_clamp_pct(a + b * xi) for xi in xs]
        beta = [a, b]
        coef = {
            "intercepto_a": round(a, 4),
            "pendiente_b_mes": round(b, 4),
            **_metricas_ajuste(pcts_fit, yhat, 2),
        }
    return yhat, beta, coef, fore_direct, False


def _forecast_proporcion_horizonte(
    modelo: ModeloProp,
    meses_fit: list[str],
    pcts_fit: list[float],
    victimas_fit: list[int],
    fatales_fit: list[int],
    beta: list[float],
    yhat: list[float],
    horizonte: int,
    fore_direct: list[float] | None,
) -> list[float]:
    if fore_direct is not None:
        return fore_direct
    if modelo == "logistica":
        return _forecast_logistica(beta, meses_fit, horizonte)
    if modelo == "logit_offset":
        return _forecast_logit_offset(meses_fit, beta, horizonte)
    if modelo == "ratio_compuesto":
        return _forecast_ratio_compuesto(meses_fit, victimas_fit, fatales_fit, horizonte)
    return _forecast_proporcion(modelo, meses_fit, pcts_fit, beta, yhat, horizonte)


def _forecast_proporcion_from_train(
    meses_train: list[str],
    pcts_train: list[float],
    victimas_train: list[int],
    fatales_train: list[int],
    modelo: ModeloProp,
    horizonte: int,
    ventana_ma: int,
    arima_opciones: ArimaOpciones | None = None,
) -> list[float] | None:
    yhat, beta, _, fore_direct, sin_modelo = _ajustar_proporcion(
        modelo,
        meses_train,
        pcts_train,
        victimas_train,
        fatales_train,
        ventana_ma,
        horizonte,
        arima_opciones,
    )
    if sin_modelo:
        return None
    return _forecast_proporcion_horizonte(
        modelo,
        meses_train,
        pcts_train,
        victimas_train,
        fatales_train,
        beta,
        yhat,
        horizonte,
        fore_direct,
    )


def _evaluar_holdout_proporcion(
    meses_fit: list[str],
    pcts_fit: list[float],
    victimas_fit: list[int],
    fatales_fit: list[int],
    modelo: ModeloProp,
    holdout_meses: int,
    ventana_ma: int,
    mape_in_sample: float | None = None,
    arima_opciones: ArimaOpciones | None = None,
) -> dict[str, Any]:
    h = _clamp_holdout_meses(holdout_meses)
    n = len(meses_fit)
    min_train = _min_meses_proporcion(modelo, ventana_ma)
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
    train_meses = meses_fit[:-h]
    train_pcts = pcts_fit[:-h]
    train_vic = victimas_fit[:-h]
    train_fat = fatales_fit[:-h]
    test_meses = meses_fit[-h:]
    test_vals = pcts_fit[-h:]

    fore = _forecast_proporcion_from_train(
        train_meses,
        train_pcts,
        train_vic,
        train_fat,
        modelo,
        h,
        ventana_ma,
        arima_opciones,
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
        err_pct = round(100.0 * abs(obs - pred) / obs, 2) if obs > 0.01 else None
        filas.append(
            {
                "mes_clave": mk,
                "mes_etiqueta": _etiqueta_mes_ym(mk),
                "observados": round(obs, 2),
                "predichos": round(pred, 2),
                "error_abs": round(abs(obs - pred), 2),
                "error_pct": err_pct,
                "unidad": "pct",
            }
        )

    mape_hold = metricas.get("mape_pct")
    precision_est = (
        round(max(0.0, min(100.0, 100.0 - float(mape_hold))), 2)
        if mape_hold is not None
        else None
    )
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
        "cumple_umbral_80": precision_est is not None and precision_est >= 80.0,
        "bondad_nivel": metricas.get("bondad_nivel"),
        "interpretacion_holdout": _interpretacion_holdout(
            float(mape_hold) if mape_hold is not None else None,
            mape_in_sample,
        ),
        "metodo": (
            f"Se entrenó con {len(train_meses)} meses (hasta {_etiqueta_mes_ym(train_meses[-1])}) "
            f"y se comparó la predicción del % con los últimos {h} meses reservados."
        ),
        "unidad": "pct",
    }


def _aplicar_bandas_proyeccion(
    proyeccion: list[dict[str, Any]],
    rmse: float | None,
) -> None:
    if rmse is None or rmse <= 0:
        return
    for row in proyeccion:
        pct = float(row.get("pct_fatales_proyectado") or row.get("ajuste_pct") or 0)
        row["pct_banda_inf"] = round(_clamp_pct(pct - Z_BANDA_CONFIANZA * rmse), 2)
        row["pct_banda_sup"] = round(_clamp_pct(pct + Z_BANDA_CONFIANZA * rmse), 2)


def _clamp_pct(y: float) -> float:
    return max(0.0, min(100.0, y))


def _min_meses_proporcion(modelo: ModeloProp, ventana_ma: int = MA_VENTANA_DEFAULT) -> int:
    if modelo in ("logit_offset", "ratio_compuesto"):
        return 3
    return _min_meses_modelo(modelo, ventana_ma)  # type: ignore[arg-type]


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
    if modelo == "logit_offset":
        return (
            "Regresión WLS sobre logit(%) con peso = víctimas del mes (exposición): pondera meses "
            "con más víctimas y captura estacionalidad calendario. Recomendado cuando el denominador varía."
        )
    if modelo == "ratio_compuesto":
        return (
            "Proyección estacional independiente de víctimas fatales y de víctimas totales; "
            "el % proyectado = 100 × fatales_proy / víctimas_proy. Coherente con la sección 1."
        )
    if modelo == "media_movil":
        return (
            "Media móvil simple del % mensual (ventana k meses): suaviza la serie y proyecta "
            "un nivel constante igual a la media de los k meses más recientes del ajuste."
        )
    if modelo == "arima":
        return (
            "ARIMA sobre la serie mensual de % fatales (escala 0–100): modela dependencia "
            "temporal y tendencia con diferenciación; requiere al menos 12 meses válidos en el ajuste."
        )
    if modelo == "sarima":
        return (
            "SARIMA con estacionalidad mensual (periodo 12) sobre % fatales: captura ciclos "
            "calendario además de la dinámica de corto plazo; requiere al menos 24 meses válidos."
        )
    return (
        "Regresión lineal del % mensual frente al índice de mes 0…n−1 en el periodo de ajuste; "
        "extrapolación lineal de la tendencia. No captura estacionalidad ni picos aislados."
    )


def _leyenda_grafico_proporcion() -> str:
    return (
        "Azul: % real del mes (fatales entre las víctimas registradas). "
        "Rojo: ajuste del modelo en el pasado y continuación hacia los próximos meses del horizonte. "
        "Sombreado rosado (si hay): margen aproximado de error (±1,96 veces el RMSE del ajuste). "
        "Un pico aislado —por ejemplo en 2020— no debe leerse como tendencia definitiva."
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
    elif modelo == "logit_offset":
        texto += (
            " Logit con exposición pondera meses con más víctimas; suele mejorar la lectura "
            "cuando el % es muy bajo y el denominador varía."
        )
    elif modelo == "ratio_compuesto":
        texto += (
            " El ratio compuesto separa volumen (víctimas) de gravedad (fatales); "
            "compare con estacional directo sobre el %."
        )
    elif modelo == "logistica":
        texto += (
            " En % fatales muy volátil, logit-lineal suele verse como línea casi plana y R² "
            "cercano a cero; no indica error del sistema sino poca tendencia estable."
        )
    elif modelo == "media_movil":
        texto += (
            " La media móvil sobre % fatales es una línea base simple: útil para leer el nivel "
            "reciente sin forzar tendencia lineal ni estacionalidad."
        )
    elif modelo in ("arima", "sarima"):
        texto += (
            " ARIMA/SARIMA sobre % fatales modelan la dinámica temporal de la gravedad relativa; "
            "R² moderado es habitual porque el % mensual es muy volátil."
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
    meta["modelos_alternativos_p07"] = ["logit_offset", "ratio_compuesto", "media_movil"]
    meta["umbrales_r2_p07"] = {
        "bueno": "≥ 0,55 — ajuste consistente del % en el periodo",
        "moderado": "0,35 – 0,54 — habitual; sirve para patrón mensual, no cifra exacta",
        "bajo": "< 0,35 — revise estacional, periodo más largo o excluir COVID del ajuste",
    }
    if sin_modelo:
        meta["bondad_nivel"] = "bajo"
        min_req = _min_meses_proporcion(modelo, int(meta.get("ventana_meses") or MA_VENTANA_DEFAULT))
        meta["interpretacion_bondad"] = (
            f"No hay al menos {min_req} meses con ≥ {MIN_VICTIMAS_MES} víctimas "
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
        elif modelo == "media_movil" and beta:
            y = beta[0]
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
    ventana_ma: int = MA_VENTANA_DEFAULT,
    arima_opciones: ArimaOpciones | None = None,
    holdout_meses: int = HOLDOUT_MESES_DEFAULT,
    evaluar_holdout: bool = True,
) -> dict[str, Any]:
    hm = max(1, min(12, int(horizonte_meses)))
    ventana = _clamp_ventana_ma(ventana_ma)
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

    min_req = _min_meses_proporcion(modelo, ventana)
    sin_modelo = len(meses_fit) < min_req
    proyeccion: list[dict[str, Any]] = []
    coeficientes: dict[str, Any] | None = None
    fore_direct: list[float] | None = None

    if not sin_modelo:
        yhat, beta, coeficientes, fore_direct, sin_modelo = _ajustar_proporcion(
            modelo,
            meses_fit,
            pcts_fit,
            victimas_fit,
            fatales_fit,
            ventana,
            hm,
            arima_opciones,
        )

        if not sin_modelo:
            yhat = [_clamp_pct(v) for v in yhat]
            yhat_by_mes = {mk: round(yhat[i], 2) for i, mk in enumerate(meses_fit)}
            for row in serie_historica:
                if row["mes_clave"] in yhat_by_mes:
                    row["ajuste_pct"] = yhat_by_mes[row["mes_clave"]]

            _puente_ajuste_hasta_fin_rango(serie_historica, meses_fit, yhat)

            fore_vals = _forecast_proporcion_horizonte(
                modelo,
                meses_fit,
                pcts_fit,
                victimas_fit,
                fatales_fit,
                beta,
                yhat,
                hm,
                fore_direct,
            )

            ultimo_ajuste_rango = serie_historica[-1].get("ajuste_pct") if serie_historica else None
            mk = meses_all[-1]
            for i, fv in enumerate(fore_vals):
                mk = _next_month_clave(mk)
                pct_proj = round(_clamp_pct(fv), 2)
                if i == 0 and ultimo_ajuste_rango is not None and pct_proj == 0 and ultimo_ajuste_rango > 0:
                    pct_proj = round(_clamp_pct(ultimo_ajuste_rango), 2)
                proyeccion.append(
                    {
                        "mes_clave": mk,
                        "mes_etiqueta": _etiqueta_mes_ym(mk),
                        "pct_fatales_proyectado": pct_proj,
                        "ajuste_pct": pct_proj,
                    }
                )

            rmse = coeficientes.get("rmse") if coeficientes else None
            _aplicar_bandas_proyeccion(proyeccion, float(rmse) if rmse is not None else None)

    meta: dict[str, Any] = {
        "modelo": modelo,
        "sin_modelo": sin_modelo,
        "min_victimas_mes": MIN_VICTIMAS_MES,
        "n_meses_ajuste": len(meses_fit),
        "n_meses_con_pct_observado": sum(1 for r in serie_historica if r.get("pct_fatales") is not None),
        "excluir_covid_ajuste": excluir_covid,
        "coeficientes": coeficientes,
        "limitaciones": (
            "Indicador orientativo: resume gravedad relativa del periodo, no riesgo individual. "
            f"Meses con menos de {MIN_VICTIMAS_MES} víctimas se muestran pero no entran al ajuste. "
            "Prefiera estacional, logit con exposición o ratio compuesto; compare siempre la prueba con meses reservados."
        ),
    }
    if len(meses_fit) < MESES_AJUSTE_RECOMENDADOS:
        meta["aviso_rango_corto"] = (
            f"Solo {len(meses_fit)} meses en el ajuste; se recomiendan ≥ {MESES_AJUSTE_RECOMENDADOS} "
            "meses útiles (con exclusión COVID) para lecturas estables."
        )
    _aplicar_meta_interpretacion(meta, modelo, coeficientes, sin_modelo)
    if comuna_id is not None:
        meta["comuna_id"] = comuna_id
        meta["comuna_nombre"] = comuna_nombre
    if modelo == "media_movil":
        meta["ventana_meses"] = ventana

    if evaluar_holdout and not sin_modelo and coeficientes:
        mape_in = coeficientes.get("mape_pct")
        meta["holdout"] = _evaluar_holdout_proporcion(
            meses_fit,
            pcts_fit,
            victimas_fit,
            fatales_fit,
            modelo,
            holdout_meses,
            ventana,
            float(mape_in) if mape_in is not None else None,
            arima_opciones,
        )
    elif evaluar_holdout:
        meta["holdout"] = {
            "activo": False,
            "holdout_meses": _clamp_holdout_meses(holdout_meses),
            "motivo": "No hay modelo ajustado para evaluar la prueba con meses reservados.",
        }

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
    ventana_ma: int = MA_VENTANA_DEFAULT,
    arima_opciones: ArimaOpciones | None = None,
    holdout_meses: int = HOLDOUT_MESES_DEFAULT,
    evaluar_holdout: bool = True,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    _MODELOS: tuple[str, ...] = (
        "ols",
        "logistica",
        "estacional",
        "logit_offset",
        "ratio_compuesto",
        "media_movil",
        "arima",
        "sarima",
    )
    mod: ModeloProp = modelo if modelo in _MODELOS else "estacional"  # type: ignore[assignment]
    ventana = _clamp_ventana_ma(ventana_ma)
    holdout = _clamp_holdout_meses(holdout_meses)

    if desglose_comuna and filtros.comuna_id is None:
        from .prioridad_territorial import _query_totales_territorio

        totales = _query_totales_territorio(inicio, fin, filtros, "comuna")
        series: list[dict[str, Any]] = []
        for tid, t in sorted(totales.items(), key=lambda x: -x[1]["incidentes"])[:10]:
            bloque = _build_proporcion_single(
                inicio,
                fin,
                filtros,
                horizonte_meses,
                mod,
                excluir_covid,
                tid,
                t["nombre"],
                ventana_ma=ventana,
                arima_opciones=arima_opciones,
                holdout_meses=holdout,
                evaluar_holdout=evaluar_holdout,
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
                "holdout_meses": holdout,
            },
            "series_por_comuna": series,
            "serie_historica": [],
            "proyeccion": [],
        }

    bloque = _build_proporcion_single(
        inicio,
        fin,
        filtros,
        horizonte_meses,
        mod,
        excluir_covid,
        None,
        None,
        ventana_ma=ventana,
        arima_opciones=arima_opciones,
        holdout_meses=holdout,
        evaluar_holdout=evaluar_holdout,
    )
    bloque["meta"] = {
        "fecha_inicio": inicio.isoformat(),
        "fecha_fin": fin.isoformat(),
        "horizonte_meses": max(1, min(12, int(horizonte_meses))),
        "holdout_meses": holdout,
        "modelo": mod,
        "desglose_comuna": False,
        **bloque["meta"],
        "filtros": meta_filtros_dict(filtros),
        "nota_territorio": nota_modo_territorio(filtros.modo_territorio),
    }
    return bloque
