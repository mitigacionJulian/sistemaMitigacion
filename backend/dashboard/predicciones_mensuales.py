"""
Proyección descriptiva mensual (Fase A: P02–P04, P06).

Modelos: OLS lineal (P01), tendencia + estacionalidad por mes calendario (P02),
Poisson log-lineal (P04). Variables: incidentes, víctimas, víctimas fatales (P03).
Desglose opcional por clase de incidente (P06).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Any, Literal

from django.db import connection

from .evolucion_mensual import _etiqueta_mes_ym, _iter_meses_clave
from .kpis import FiltrosKpi, _fatal_sql_expr

ModeloPred = Literal["ols", "estacional", "poisson"]
VariablePred = Literal["incidentes", "victimas", "victimas_fatales"]

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

    if filtros.comuna_id is not None:
        where.append("i.comuna_id = %s")
        params.append(filtros.comuna_id)
    if filtros.barrio_id is not None:
        where.append("i.barrio_id = %s")
        params.append(filtros.barrio_id)
    if filtros.clase_incidente_id is not None:
        where.append("i.clase_incidente_id = %s")
        params.append(filtros.clase_incidente_id)
    if filtros.via_id is not None:
        where.append("i.via_id = %s")
        params.append(filtros.via_id)
    if filtros.punto_critico_id is not None:
        where.append("i.punto_critico_id = %s")
        params.append(filtros.punto_critico_id)

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
    LEFT JOIN victima v ON v.incidente_id = i.id
    LEFT JOIN gravedad_victima gv ON v.gravedad_victima_id = gv.id
    WHERE {wh}
    GROUP BY to_char(i.fecha_incidente, 'YYYY-MM')
    ORDER BY mes
    """
    out: dict[str, int] = {}
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        for row in cursor.fetchall():
            out[str(row[0])] = int(row[1] or 0)
    return out


def _query_clases_con_datos(inicio: date, fin: date, filtros: FiltrosKpi) -> list[tuple[int, str, int]]:
    """(clase_id, nombre, total incidentes en rango) ordenado por volumen desc."""
    filtros = filtros or FiltrosKpi()
    where = ["i.fecha_incidente >= %s", "i.fecha_incidente <= %s", "i.clase_incidente_id IS NOT NULL"]
    params: list[Any] = [inicio, fin]
    if filtros.comuna_id is not None:
        where.append("i.comuna_id = %s")
        params.append(filtros.comuna_id)
    if filtros.barrio_id is not None:
        where.append("i.barrio_id = %s")
        params.append(filtros.barrio_id)
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


def _ols_intercept_slope(xs: list[float], ys: list[float]) -> tuple[float, float]:
    n = len(xs)
    sum_x = sum(xs)
    sum_y = sum(ys)
    sum_xx = sum(x * x for x in xs)
    sum_xy = sum(x * y for x, y in zip(xs, ys))
    denom = n * sum_xx - sum_x * sum_x
    if abs(denom) < 1e-15:
        return sum_y / n, 0.0
    b = (n * sum_xy - sum_x * sum_y) / denom
    a = (sum_y - b * sum_x) / n
    return a, b


def _r_squared(ys: list[float], yhat: list[float]) -> float:
    if not ys or len(ys) != len(yhat):
        return 0.0
    mean_y = sum(ys) / len(ys)
    ss_tot = sum((y - mean_y) ** 2 for y in ys)
    if ss_tot < 1e-15:
        return 1.0
    ss_res = sum((y - yh) ** 2 for y, yh in zip(ys, yhat))
    return max(0.0, min(1.0, 1.0 - ss_res / ss_tot))


def _rmse(ys: list[float], yhat: list[float]) -> float:
    if not ys:
        return 0.0
    return math.sqrt(sum((y - yh) ** 2 for y, yh in zip(ys, yhat)) / len(ys))


def _mape_pct(ys: list[float], yhat: list[float]) -> float | None:
    errs = [abs(y - yh) / y for y, yh in zip(ys, yhat) if y > 0]
    if not errs:
        return None
    return 100.0 * sum(errs) / len(errs)


def _interpretacion_bondad(r2: float, mape: float | None) -> dict[str, str]:
    """Texto corto para sustentación según umbrales de R² (series mensuales de conteo)."""
    if r2 >= 0.55:
        nivel = "bueno"
        texto = (
            "Ajuste bueno para un tablero exploratorio: el modelo reproduce de forma consistente "
            "la serie histórica en el periodo y filtros elegidos."
        )
    elif r2 >= 0.35:
        nivel = "moderado"
        texto = (
            "Ajuste moderado (habitual con estacionalidad y meses atípicos): sirve para tendencia, "
            "comparar escenarios y orden de magnitud; no para cifras exactas mes a mes."
        )
    else:
        nivel = "bajo"
        texto = (
            "Ajuste bajo: conviene modelo estacional, excluir meses COVID del ajuste, ampliar fechas "
            "o revisar filtros antes de usar la proyección con confianza."
        )

    if mape is not None:
        if mape <= 12:
            texto += f" Error relativo medio (MAPE) aceptable: {mape:g}%."
        elif mape <= 20:
            texto += f" MAPE moderado: {mape:g}%."
        else:
            texto += f" MAPE elevado ({mape:g}%): la serie es difícil de resumir con este modelo simple."

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


def _solve_design_ols(x: list[list[float]], ys: list[float]) -> list[float] | None:
    n = len(ys)
    p = len(x[0])
    return _solve_linear_system(
        [[sum(x[k][c] * x[k][r] for k in range(n)) for r in range(p)] for c in range(p)],
        [sum(x[k][c] * ys[k] for k in range(n)) for c in range(p)],
    )


def _predict_linear(beta: list[float], row: list[float]) -> float:
    return max(0.0, sum(b * xv for b, xv in zip(beta, row)))


def _solve_linear_system(a: list[list[float]], b: list[float]) -> list[float] | None:
    """Eliminación gaussiana; a es n×n, b longitud n."""
    n = len(b)
    if n == 0:
        return []
    mat = [row[:] + [bv] for row, bv in zip(a, b)]
    for col in range(n):
        pivot = col
        for r in range(col + 1, n):
            if abs(mat[r][col]) > abs(mat[pivot][col]):
                pivot = r
        if abs(mat[pivot][col]) < 1e-12:
            return None
        mat[col], mat[pivot] = mat[pivot], mat[col]
        div = mat[col][col]
        for j in range(col, n + 1):
            mat[col][j] /= div
        for r in range(n):
            if r == col:
                continue
            factor = mat[r][col]
            for j in range(col, n + 1):
                mat[r][j] -= factor * mat[col][j]
    return [mat[i][n] for i in range(n)]


def _mat_vec_mul(a: list[list[float]], x: list[float]) -> list[float]:
    return [sum(ai * xj for ai, xj in zip(row, x)) for row in a]


def _normal_equations_solve(
    x: list[list[float]],
    y_work: list[float],
    weights: list[float],
) -> list[float] | None:
    n = len(y_work)
    p = len(x[0])
    a = [[0.0] * p for _ in range(p)]
    b = [0.0] * p
    for k in range(n):
        w = weights[k]
        for c in range(p):
            b[c] += w * x[k][c] * y_work[k]
            for r in range(p):
                a[c][r] += w * x[k][c] * x[k][r]
    return _solve_linear_system(a, b)


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
        else:
            y = yhat_hist[-1] if yhat_hist else 0.0
        fore.append(round(y, 2))
    return fore


def _row_historica(mk: str, obs: int, ajuste: float | None, variable: VariablePred) -> dict[str, Any]:
    row: dict[str, Any] = {
        "mes_clave": mk,
        "mes_etiqueta": _etiqueta_mes_ym(mk),
        "observados": obs,
        "ajuste_modelo": ajuste,
    }
    if variable == "incidentes":
        row["incidentes_observados"] = obs
        row["incidentes_ajuste_lineal"] = ajuste
    return row


def _row_proyeccion(mk: str, valor: float, variable: VariablePred) -> dict[str, Any]:
    row: dict[str, Any] = {
        "mes_clave": mk,
        "mes_etiqueta": _etiqueta_mes_ym(mk),
        "proyectados": valor,
        "ajuste_modelo": valor,
    }
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
    return base + " Poisson asume varianza≈media; si hay sobredispersión, la incertidumbre puede subestimarse."


def _min_meses_modelo(modelo: ModeloPred) -> int:
    if modelo == "ols":
        return 2
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
) -> dict[str, Any]:
    hm = max(1, min(12, int(horizonte_meses)))
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
        n_fit < _min_meses_modelo(modelo)
        or (modelo == "poisson" and sum(valores_fit) == 0)
    )
    serie_historica: list[dict[str, Any]] = []
    proyeccion: list[dict[str, Any]] = []
    coeficientes: dict[str, Any] | None = None
    beta: list[float] = []
    yhat_by_mes: dict[str, float] = {}

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
        else:
            yhat_fit, beta, coeficientes = _fit_poisson(serie_fit)
            for i, mk in enumerate(meses_fit):
                yhat_by_mes[mk] = yhat_fit[i]

        for i, mk in enumerate(meses):
            ajuste = round(yhat_by_mes[mk], 2) if mk in yhat_by_mes else None
            serie_historica.append(_row_historica(mk, valores[i], ajuste, variable))

        yhat_hist_list = [yhat_by_mes[mk] for mk in meses_fit]
        modelo_forecast: ModeloPred = modelo
        if modelo == "poisson" and coeficientes and coeficientes.get("fallback_estacional"):
            modelo_forecast = "estacional"
        fore = _forecast_values(modelo_forecast, serie_fit, beta, hm, yhat_hist_list)
        mk = meses[-1]
        for yf in fore:
            mk = _next_month_clave(mk)
            proyeccion.append(_row_proyeccion(mk, yf, variable))
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
            "filtros": {
                "comuna_id": filtros.comuna_id,
                "barrio_id": filtros.barrio_id,
                "clase_incidente_id": filtros.clase_incidente_id,
            },
        }
    if coeficientes:
        meta["interpretacion_bondad"] = coeficientes.get("interpretacion_bondad")
        meta["bondad_nivel"] = coeficientes.get("bondad_nivel")

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
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    mod: ModeloPred = modelo if modelo in ("ols", "estacional", "poisson") else "ols"
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
            )
            bloque = _build_single(
                inicio, fin, f_clase, horizonte_meses, mod, var, excluir_covid=excluir_covid
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
                "filtros": {
                    "comuna_id": filtros.comuna_id,
                    "barrio_id": filtros.barrio_id,
                    "clase_incidente_id": None,
                },
            },
            "series_por_clase": series_por_clase,
            "serie_historica": [],
            "proyeccion": [],
        }

    bloque = _build_single(
        inicio, fin, filtros, horizonte_meses, mod, var, excluir_covid=excluir_covid
    )
    bloque["meta"]["desglose_clase"] = False
    return bloque


# Compatibilidad tests que parchean agregación mensual de incidentes
def _query_agregado_por_mes(inicio: date, fin: date, filtros: FiltrosKpi) -> dict[str, tuple[int, int]]:
    raw = _query_mensual_valores(inicio, fin, filtros, "incidentes")
    return {k: (v, 0) for k, v in raw.items()}
