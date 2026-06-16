"""
ARIMA / SARIMA para proyección mensual de series de conteo.

Órdenes por defecto (exploratorio, sin auto-ARIMA):
  - ARIMA(1,1,1)
  - SARIMA(1,1,1)(1,1,1,12)

Si el ajuste falla, se intenta (0,1,1) y variante estacional (0,1,1,12).
"""
from __future__ import annotations

import warnings
from typing import Any

MIN_MESES_ARIMA = 12
MIN_MESES_SARIMA = 24
SEASONAL_PERIOD = 12


def min_meses_requeridos(*, seasonal: bool) -> int:
    return MIN_MESES_SARIMA if seasonal else MIN_MESES_ARIMA


def _alignar_fitted(valores: list[float], fitted_raw: Any) -> list[float]:
    n = len(valores)
    if hasattr(fitted_raw, "values"):
        fitted_list = [float(x) for x in fitted_raw.values]
    elif hasattr(fitted_raw, "tolist"):
        fitted_list = [float(x) for x in fitted_raw.tolist()]
    else:
        fitted_list = [float(x) for x in fitted_raw]

    yhat = [0.0] * n
    if len(fitted_list) >= n:
        yhat = [max(0.0, fitted_list[i]) for i in range(n)]
    else:
        offset = n - len(fitted_list)
        for i in range(n):
            if i < offset:
                yhat[i] = max(0.0, float(valores[i]))
            else:
                yhat[i] = max(0.0, fitted_list[i - offset])
    return yhat


def _fit_arima_internal(
    valores: list[float],
    *,
    seasonal: bool,
) -> tuple[Any, tuple[int, int, int], tuple[int, int, int, int]] | None:
    try:
        from statsmodels.tsa.arima.model import ARIMA
    except ImportError:
        return None

    order = (1, 1, 1)
    seasonal_order: tuple[int, int, int, int] = (
        (1, 1, 1, SEASONAL_PERIOD) if seasonal else (0, 0, 0, 0)
    )
    candidatos: list[tuple[tuple[int, int, int], tuple[int, int, int, int]]] = [
        (order, seasonal_order),
        ((0, 1, 1), seasonal_order),
    ]
    if seasonal:
        candidatos.append(((1, 1, 1), (0, 1, 1, SEASONAL_PERIOD)))

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for ord_cand, seas_cand in candidatos:
            try:
                model = ARIMA(valores, order=ord_cand, seasonal_order=seas_cand)
                res = model.fit()
                if res is not None:
                    return res, ord_cand, seas_cand
            except Exception:
                continue
    return None


def ajustar_y_proyectar_arima(
    valores: list[float],
    horizonte: int,
    *,
    seasonal: bool,
    valor_min: float = 0.0,
    valor_max: float | None = None,
) -> tuple[list[float], list[float], dict[str, Any]] | None:
    """
    Ajusta ARIMA o SARIMA y devuelve (yhat_histórico, proyección, coeficientes).
    valor_max opcional (p. ej. 100 para % fatales).
    """

    def _clamp_val(x: float) -> float:
        y = max(valor_min, float(x))
        if valor_max is not None:
            y = min(valor_max, y)
        return y

    from .predicciones_mensuales import _interpretacion_bondad, _metricas_ajuste

    n = len(valores)
    if n < min_meses_requeridos(seasonal=seasonal):
        return None

    ys = [float(v) for v in valores]
    fit = _fit_arima_internal(ys, seasonal=seasonal)
    if fit is None:
        return None

    res, order, seasonal_order = fit
    yhat = [_clamp_val(x) for x in _alignar_fitted(ys, res.fittedvalues)]

    fc_raw = res.forecast(steps=horizonte)
    if hasattr(fc_raw, "values"):
        fc_list = [float(x) for x in fc_raw.values]
    elif hasattr(fc_raw, "tolist"):
        fc_list = [float(x) for x in fc_raw.tolist()]
    else:
        fc_list = [float(x) for x in fc_raw]

    fore = [round(_clamp_val(x), 2) for x in fc_list]

    n_params = sum(order) + (sum(seasonal_order[:3]) if seasonal else 0)
    coeficientes = {
        "orden_arima": list(order),
        "orden_estacional": list(seasonal_order) if seasonal else None,
        "aic": round(float(res.aic), 2) if res.aic is not None else None,
        "bic": round(float(res.bic), 2) if res.bic is not None else None,
        **_metricas_ajuste(ys, yhat, max(n_params, 2)),
    }
    bondad = _interpretacion_bondad(coeficientes["r2"], coeficientes.get("mape_pct"))
    coeficientes.update(bondad)
    coeficientes["nota"] = (
        f"ARIMA{order}"
        + (f"×{seasonal_order}" if seasonal else "")
        + ". Criterios AIC/BIC orientan comparación entre órdenes probados; "
        "no garantizan validez causal."
    )

    return yhat, fore, coeficientes
