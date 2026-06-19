"""
ARIMA / SARIMA para proyección mensual de series de conteo.

Órdenes por defecto (exploratorio, sin auto-ARIMA):
  - ARIMA(2,1,3)
  - SARIMA(2,1,3)(1,1,1,12)

Si el ajuste falla, se intenta (1,1,1), luego (0,1,1) y variantes estacionales.
"""
from __future__ import annotations

import warnings
from typing import Any

MIN_MESES_ARIMA = 12
MIN_MESES_SARIMA = 24
SEASONAL_PERIOD = 12

ARIMA_ORDER_DEFAULT: tuple[int, int, int] = (2, 1, 3)
SARIMA_SEASONAL_DEFAULT: tuple[int, int, int, int] = (1, 1, 1, SEASONAL_PERIOD)
MAX_ARIMA_ORDEN = 6


def _parse_enteros_orden(raw: str, n: int) -> list[int] | None:
    limpio = raw.strip().replace("(", "").replace(")", "").replace("×", ",")
    partes = [p.strip() for p in limpio.replace(";", ",").split(",") if p.strip()]
    if len(partes) != n:
        return None
    try:
        nums = [int(float(p)) for p in partes]
    except (TypeError, ValueError):
        return None
    if any(v < 0 or v > MAX_ARIMA_ORDEN for v in nums):
        return None
    return nums


def parse_arima_order(raw: str | None) -> tuple[int, int, int] | None:
    if raw is None or not str(raw).strip():
        return None
    nums = _parse_enteros_orden(str(raw), 3)
    if nums is None:
        return None
    return nums[0], nums[1], nums[2]


def parse_sarima_seasonal(raw: str | None) -> tuple[int, int, int, int] | None:
    if raw is None or not str(raw).strip():
        return None
    limpio = str(raw).strip().replace("(", "").replace(")", "").replace("×", ",")
    partes = [p.strip() for p in limpio.replace(";", ",").split(",") if p.strip()]
    if len(partes) != 4:
        return None
    try:
        nums = [int(float(p)) for p in partes]
    except (TypeError, ValueError):
        return None
    if any(v < 0 or v > MAX_ARIMA_ORDEN for v in nums[:3]):
        return None
    if nums[3] != SEASONAL_PERIOD:
        return None
    return nums[0], nums[1], nums[2], nums[3]


def _candidatos_ajuste(
    *,
    seasonal: bool,
    order: tuple[int, int, int] | None,
    seasonal_order: tuple[int, int, int, int] | None,
) -> list[tuple[tuple[int, int, int], tuple[int, int, int, int]]]:
    ord_base = order or ARIMA_ORDER_DEFAULT
    seas_base: tuple[int, int, int, int] = (
        seasonal_order
        if seasonal_order is not None
        else (SARIMA_SEASONAL_DEFAULT if seasonal else (0, 0, 0, 0))
    )
    usa_defaults = ord_base == ARIMA_ORDER_DEFAULT and (
        not seasonal or seas_base == SARIMA_SEASONAL_DEFAULT
    )
    if usa_defaults:
        candidatos: list[tuple[tuple[int, int, int], tuple[int, int, int, int]]] = [
            (ARIMA_ORDER_DEFAULT, seas_base),
            ((1, 1, 1), seas_base),
            ((0, 1, 1), seas_base),
        ]
        if seasonal:
            candidatos.insert(1, (ARIMA_ORDER_DEFAULT, (0, 1, 1, SEASONAL_PERIOD)))
            candidatos.append(((1, 1, 1), (0, 1, 1, SEASONAL_PERIOD)))
        return candidatos

    candidatos = [(ord_base, seas_base), ((1, 1, 1), seas_base), ((0, 1, 1), seas_base)]
    if seasonal:
        candidatos.append((ord_base, (0, 1, 1, SEASONAL_PERIOD)))
    return candidatos


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
    order: tuple[int, int, int] | None = None,
    seasonal_order: tuple[int, int, int, int] | None = None,
) -> tuple[Any, tuple[int, int, int], tuple[int, int, int, int]] | None:
    try:
        from statsmodels.tsa.arima.model import ARIMA
    except ImportError:
        return None

    candidatos = _candidatos_ajuste(
        seasonal=seasonal,
        order=order,
        seasonal_order=seasonal_order,
    )

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
    order: tuple[int, int, int] | None = None,
    seasonal_order: tuple[int, int, int, int] | None = None,
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
    order_sol = order
    seasonal_order_sol = seasonal_order
    fit = _fit_arima_internal(
        ys,
        seasonal=seasonal,
        order=order_sol,
        seasonal_order=seasonal_order_sol,
    )
    if fit is None:
        return None

    res, order_fit, seasonal_order_fit = fit
    yhat = [_clamp_val(x) for x in _alignar_fitted(ys, res.fittedvalues)]

    fc_raw = res.forecast(steps=horizonte)
    if hasattr(fc_raw, "values"):
        fc_list = [float(x) for x in fc_raw.values]
    elif hasattr(fc_raw, "tolist"):
        fc_list = [float(x) for x in fc_raw.tolist()]
    else:
        fc_list = [float(x) for x in fc_raw]

    fore = [round(_clamp_val(x), 2) for x in fc_list]

    n_params = sum(order_fit) + (sum(seasonal_order_fit[:3]) if seasonal else 0)
    coeficientes = {
        "orden_arima": list(order_fit),
        "orden_estacional": list(seasonal_order_fit) if seasonal else None,
        "orden_arima_solicitado": list(order_sol or ARIMA_ORDER_DEFAULT),
        "orden_estacional_solicitado": (
            list(seasonal_order_sol if seasonal_order_sol is not None else SARIMA_SEASONAL_DEFAULT)
            if seasonal
            else None
        ),
        "aic": round(float(res.aic), 2) if res.aic is not None else None,
        "bic": round(float(res.bic), 2) if res.bic is not None else None,
        **_metricas_ajuste(ys, yhat, max(n_params, 2)),
    }
    bondad = _interpretacion_bondad(coeficientes["r2"], coeficientes.get("mape_pct"))
    coeficientes.update(bondad)
    coeficientes["nota"] = (
        f"ARIMA{tuple(order_fit)}"
        + (f"×{tuple(seasonal_order_fit)}" if seasonal else "")
        + ". Criterios AIC/BIC orientan comparación entre órdenes probados; "
        "no garantizan validez causal."
    )

    return yhat, fore, coeficientes
