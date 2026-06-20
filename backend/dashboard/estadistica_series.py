"""
Utilidades numéricas para modelos de series mensuales (numpy).

Centraliza OLS, desviación estándar muestral y resolución de diseños lineales
con mayor estabilidad numérica que eliminación gaussiana manual.
"""
from __future__ import annotations

import math

import numpy as np


def ols_intercept_slope(xs: list[float], ys: list[float]) -> tuple[float, float]:
    x = np.asarray(xs, dtype=np.float64)
    y = np.asarray(ys, dtype=np.float64)
    n = len(y)
    if n == 0:
        return 0.0, 0.0
    if n == 1:
        return float(y[0]), 0.0
    design = np.column_stack([np.ones(n, dtype=np.float64), x])
    beta, *_ = np.linalg.lstsq(design, y, rcond=None)
    return float(beta[0]), float(beta[1])


def solve_design_ols(x: list[list[float]], ys: list[float]) -> list[float] | None:
    if not x or not ys:
        return None
    X = np.asarray(x, dtype=np.float64)
    y = np.asarray(ys, dtype=np.float64)
    n, p = X.shape
    if n < p:
        return None
    beta, _, rank, _ = np.linalg.lstsq(X, y, rcond=None)
    if rank < p:
        return None
    return [float(v) for v in beta]


def sample_mean(ys: list[float]) -> float:
    if not ys:
        return 0.0
    return float(np.mean(np.asarray(ys, dtype=np.float64)))


def sample_std(ys: list[float]) -> float:
    if len(ys) < 2:
        return 0.0
    return float(np.std(np.asarray(ys, dtype=np.float64), ddof=1))


def r_squared(ys: list[float], yhat: list[float]) -> float:
    if not ys or len(ys) != len(yhat):
        return 0.0
    y = np.asarray(ys, dtype=np.float64)
    yh = np.asarray(yhat, dtype=np.float64)
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    if ss_tot < 1e-15:
        return 1.0
    ss_res = float(np.sum((y - yh) ** 2))
    return max(0.0, min(1.0, 1.0 - ss_res / ss_tot))


def rmse(ys: list[float], yhat: list[float]) -> float:
    if not ys:
        return 0.0
    y = np.asarray(ys, dtype=np.float64)
    yh = np.asarray(yhat, dtype=np.float64)
    return float(math.sqrt(float(np.mean((y - yh) ** 2))))


def mape_pct(ys: list[float], yhat: list[float]) -> float | None:
    y = np.asarray(ys, dtype=np.float64)
    yh = np.asarray(yhat, dtype=np.float64)
    mask = y > 0
    if not np.any(mask):
        return None
    errs = np.abs(y[mask] - yh[mask]) / y[mask]
    return float(100.0 * float(np.mean(errs)))


def solve_weighted_least_squares(
    x: list[list[float]],
    y_work: list[float],
    weights: list[float],
) -> list[float] | None:
    if not x or not y_work:
        return None
    X = np.asarray(x, dtype=np.float64)
    y = np.asarray(y_work, dtype=np.float64)
    w = np.sqrt(np.maximum(np.asarray(weights, dtype=np.float64), 1e-12))
    Xw = X * w[:, np.newaxis]
    yw = y * w
    beta, _, rank, _ = np.linalg.lstsq(Xw, yw, rcond=None)
    if rank < X.shape[1]:
        return None
    return [float(v) for v in beta]
