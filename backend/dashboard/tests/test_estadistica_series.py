"""Tests for estadistica_series helpers."""
from dashboard.estadistica_series import (
    ols_intercept_slope,
    sample_std,
    solve_design_ols,
)


def test_ols_linea_perfecta():
    xs = [0.0, 1.0, 2.0]
    ys = [10.0, 12.0, 14.0]
    a, b = ols_intercept_slope(xs, ys)
    assert abs(a - 10.0) < 1e-9
    assert abs(b - 2.0) < 1e-9


def test_sample_std():
    assert sample_std([100.0, 102.0, 98.0, 101.0]) > 0


def test_design_ols_rank():
    x = [[1.0, 0.0], [1.0, 1.0], [1.0, 2.0]]
    ys = [10.0, 12.0, 14.0]
    beta = solve_design_ols(x, ys)
    assert beta is not None
    assert abs(beta[0] - 10.0) < 1e-6
    assert abs(beta[1] - 2.0) < 1e-6
