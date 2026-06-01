"""
P12 — Matriz día×hora proyectada.
P13 — Proyección por día de semana (y participación en horizonte).

Reparte el total de incidentes proyectados (modelo mensual OLS/estacional/media móvil)
según el patrón histórico día×hora o día de semana del periodo filtrado.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from .evolucion_mensual import _iter_meses_clave
from .kpis import FiltrosKpi
from .matriz_dia_hora import _query_heatmap
from .por_dia_semana import (
    _DIA_LABEL,
    _PCT_UNIFORME_DIA,
    _carga_nivel_vs_uniforme,
    _query_por_dia,
)
from .predicciones_mensuales import (
    MA_VENTANA_DEFAULT,
    _build_single,
    normalize_modelo_proyeccion,
)

ModeloPatron = str  # "ols" | "estacional" | "media_movil"

_LAPLACE_CELDA = 0.5
_LAPLACE_DIA = 0.25


def _total_proyectado_horizonte(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
    horizonte_meses: int,
    modelo: ModeloPatron,
    excluir_covid: bool,
    ventana_ma: int = MA_VENTANA_DEFAULT,
) -> tuple[float | None, dict[str, Any]]:
    bloque = _build_single(
        inicio,
        fin,
        filtros,
        horizonte_meses,
        modelo,  # type: ignore[arg-type]
        "incidentes",
        excluir_covid=excluir_covid,
        ventana_ma=ventana_ma,
    )
    meta = bloque.get("meta") or {}
    if meta.get("sin_modelo"):
        return None, meta
    total = sum(float(r.get("proyectados") or 0) for r in bloque.get("proyeccion") or [])
    return total, meta


def _distribuir_enteros(pesos: list[float], total_objetivo: float) -> list[int]:
    objetivo = max(0, int(round(total_objetivo)))
    n = len(pesos)
    if n == 0:
        return []
    if objetivo == 0:
        return [0] * n
    s = sum(pesos)
    if s <= 0:
        base = objetivo // n
        rest = objetivo % n
        return [base + (1 if i < rest else 0) for i in range(n)]
    fracs = [objetivo * w / s for w in pesos]
    floors = [int(f // 1) for f in fracs]
    rest = objetivo - sum(floors)
    orden = sorted(range(n), key=lambda i: fracs[i] - floors[i], reverse=True)
    for i in orden[:rest]:
        floors[i] += 1
    return floors


def _terciles_nivel(valores: list[float]) -> tuple[float | None, float | None]:
    if not valores:
        return None, None
    s = sorted(valores)
    p33 = s[len(s) // 3]
    p66 = s[(2 * len(s)) // 3]
    return p33, p66


def _meses_en_periodo(inicio: date, fin: date) -> int:
    return max(1, len(_iter_meses_clave(inicio, fin)))


def _nivel_tercil(valor: float, p33: float, p66: float) -> str:
    if valor >= p66:
        return "alto"
    if valor >= p33:
        return "medio"
    return "bajo"


def build_matriz_dia_hora_proyectada_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
    horizonte_meses: int = 3,
    modelo: str = "estacional",
    excluir_covid: bool = True,
    ventana_ma: int = MA_VENTANA_DEFAULT,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    hm = max(1, min(12, int(horizonte_meses)))
    mod = normalize_modelo_proyeccion(modelo)

    actual = _query_heatmap(inicio, fin, filtros)
    total_hist = sum(actual.values())
    total_hor, meta_pred = _total_proyectado_horizonte(
        inicio, fin, filtros, hm, mod, excluir_covid, ventana_ma
    )

    sin_datos = total_hist == 0 or total_hor is None
    celdas = [(d, h) for d in range(7) for h in range(24)]
    pesos = [
        float(actual.get((d, h), 0) + _LAPLACE_CELDA)
        for d, h in celdas
    ]
    denom_hist = total_hist + 7 * 24 * _LAPLACE_CELDA
    proyectados = (
        [0] * len(celdas)
        if sin_datos
        else _distribuir_enteros(pesos, total_hor or 0)
    )

    vals_proj = [float(p) for p in proyectados if p > 0]
    p33, p66 = _terciles_nivel(vals_proj) if vals_proj else (None, None)
    meses_periodo = _meses_en_periodo(inicio, fin)

    serie: list[dict[str, Any]] = []
    max_obs = 0
    max_proj = 0
    suma_delta = 0
    for idx, (d, h) in enumerate(celdas):
        obs = actual.get((d, h), 0)
        proj = proyectados[idx]
        delta = proj - obs
        suma_delta += delta
        max_obs = max(max_obs, obs)
        max_proj = max(max_proj, proj)
        pct_obs = (100.0 * obs / total_hist) if total_hist > 0 else 0.0
        pct_pr = (100.0 * proj / sum(proyectados)) if sum(proyectados) > 0 else 0.0
        obs_equiv_horizonte = round(obs * hm / meses_periodo) if meses_periodo > 0 else obs
        delta_vs_tasa_equiv = proj - obs_equiv_horizonte
        nivel = (
            _nivel_tercil(float(proj), p33, p66)
            if p33 is not None and p66 is not None and proj > 0
            else "bajo"
        )
        serie.append(
            {
                "dia_semana": d,
                "hora": h,
                "incidentes_observados_periodo": obs,
                "incidentes_proyectados_horizonte": proj,
                "delta_proyeccion_menos_periodo": delta,
                "participacion_observada_pct": round(pct_obs, 3),
                "participacion_proyectada_pct": round(pct_pr, 3),
                "delta_participacion_pp": round(pct_pr - pct_obs, 3),
                "incidentes_periodo_equivalente_horizonte": obs_equiv_horizonte,
                "delta_vs_tasa_equivalente_horizonte": delta_vs_tasa_equiv,
                "nivel_carga_proyectada": nivel,
            }
        )

    suma_proj = sum(proyectados)
    coherente = suma_proj == suma_delta + total_hist

    modelo_meta_txt = mod
    if mod == "media_movil":
        modelo_meta_txt = f"media_movil (ventana {ventana_ma})"

    meta_out: dict[str, Any] = {
        "fecha_inicio": inicio.isoformat(),
        "fecha_fin": fin.isoformat(),
        "horizonte_meses": hm,
        "modelo": mod,
        "total_incidentes_periodo": total_hist,
        "total_proyectado_horizonte": round(total_hor or 0, 2) if total_hor is not None else None,
        "meses_en_periodo": meses_periodo,
        "max_observados": max_obs,
        "max_proyectados": max_proj,
        "sin_datos": sin_datos,
        "validacion_diferencia": {
            "suma_observados_periodo": total_hist,
            "suma_proyectados_horizonte": suma_proj,
            "suma_delta_celdas": suma_delta,
            "coherente": coherente,
            "formula": "delta_proyeccion_menos_periodo = incidentes_proyectados_horizonte - incidentes_observados_periodo (por celda)",
        },
        "lectura_diferencia": (
            "La matriz «Diferencia» resta, celda a celda, los incidentes del periodo seleccionado "
            f"({total_hist} en {meses_periodo} mes(es)) de la proyección repartida en el horizonte "
            f"({suma_proj} incidentes en {hm} mes(es) proyectados). "
            "No es lo mismo que comparar mes a mes: el periodo puede ser más largo que el horizonte. "
            f"La suma de todas las celdas cumple ΣΔ = proyección − periodo ({suma_delta} = {suma_proj} − {total_hist}). "
            "Para comparar solo el patrón relativo (sin el efecto del tamaño del periodo), use "
            "delta_participacion_pp en cada celda (puntos porcentuales de participación)."
        ),
        "prediccion_mensual": {
            "sin_modelo": meta_pred.get("sin_modelo"),
            "r2": meta_pred.get("r2"),
            "interpretacion_bondad": meta_pred.get("interpretacion_bondad"),
        },
        "que_mide": (
            "Distribución esperada de incidentes por día de la semana y hora en el horizonte, "
            "a partir del total proyectado por el modelo mensual y el patrón histórico del periodo."
        ),
        "metodo": (
            f"Se proyectan {hm} mes(es) de incidentes con modelo {modelo_meta_txt} (mismos filtros). "
            f"Ese total se reparte en 7×24 celdas según proporciones del periodo observado "
            f"(suavizado Laplace {_LAPLACE_CELDA} por celda). No es probabilidad individual."
        ),
        "interpretacion": (
            "Use las celdas más oscuras en «Proyección» para priorizar vigilancia operativa "
            "(franjas día×hora con mayor carga esperada). Compare con «Periodo seleccionado» "
            "y la matriz de diferencia (proyección − periodo) para ver dónde se espera más volumen futuro."
        ),
        "limitaciones": (
            "Asume que el patrón relativo día×hora del periodo filtrado se mantiene en el futuro; "
            "no modela cada celda con serie propia. Con pocos incidentes o sin modelo mensual, "
            "no hay proyección."
        ),
        "filtros": {
            "comuna_id": filtros.comuna_id,
            "barrio_id": filtros.barrio_id,
            "clase_incidente_id": filtros.clase_incidente_id,
        },
    }
    if mod == "media_movil":
        meta_out["ventana_meses"] = ventana_ma

    return {
        "meta": meta_out,
        "serie": serie,
    }


def build_dia_semana_proyectado_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
    horizonte_meses: int = 3,
    modelo: str = "estacional",
    excluir_covid: bool = True,
    ventana_ma: int = MA_VENTANA_DEFAULT,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    hm = max(1, min(12, int(horizonte_meses)))
    mod = normalize_modelo_proyeccion(modelo)

    act = _query_por_dia(inicio, fin, filtros)
    total_hist = sum(act.get(d, (0, 0))[0] for d in range(7))
    total_hor, meta_pred = _total_proyectado_horizonte(
        inicio, fin, filtros, hm, mod, excluir_covid, ventana_ma
    )

    sin_datos = total_hist == 0 or total_hor is None
    pesos = [float(act.get(d, (0, 0))[0] + _LAPLACE_DIA) for d in range(7)]
    proyectados = (
        [0] * 7
        if sin_datos
        else _distribuir_enteros(pesos, total_hor or 0)
    )
    total_proj = sum(proyectados)

    serie: list[dict[str, Any]] = []
    for d in range(7):
        inc_a = act.get(d, (0, 0))[0]
        inc_p = proyectados[d]
        pct_obs = (100.0 * inc_a / total_hist) if total_hist > 0 else 0.0
        pct_pr = (100.0 * inc_p / total_proj) if total_proj > 0 else 0.0
        ratio_obs = (pct_obs / _PCT_UNIFORME_DIA) if _PCT_UNIFORME_DIA > 0 else 0.0
        ratio_pr = (pct_pr / _PCT_UNIFORME_DIA) if _PCT_UNIFORME_DIA > 0 else 0.0
        serie.append(
            {
                "dia_semana": d,
                "dia": _DIA_LABEL[d],
                "incidentes_observados_periodo": inc_a,
                "incidentes_proyectados_horizonte": inc_p,
                "participacion_observada_pct": round(pct_obs, 2),
                "participacion_proyectada_pct": round(pct_pr, 2),
                "ratio_vs_uniforme_observado": round(ratio_obs, 3),
                "ratio_vs_uniforme_proyectado": round(ratio_pr, 3),
                "carga_dia_nivel_observado": _carga_nivel_vs_uniforme(ratio_obs),
                "carga_dia_nivel_proyectado": _carga_nivel_vs_uniforme(ratio_pr),
            }
        )

    modelo_meta_txt = mod
    if mod == "media_movil":
        modelo_meta_txt = f"media_movil (ventana {ventana_ma})"

    meta_out: dict[str, Any] = {
        "fecha_inicio": inicio.isoformat(),
        "fecha_fin": fin.isoformat(),
        "horizonte_meses": hm,
        "modelo": mod,
        "total_incidentes_periodo": total_hist,
        "total_proyectado_horizonte": round(total_hor or 0, 2) if total_hor is not None else None,
        "sin_datos": sin_datos,
        "prediccion_mensual": {
            "sin_modelo": meta_pred.get("sin_modelo"),
            "r2": meta_pred.get("r2"),
            "interpretacion_bondad": meta_pred.get("interpretacion_bondad"),
        },
        "que_mide": (
            "Incidentes esperados por día de la semana en el horizonte de predicción, "
            "repartidos según la concentración observada en el periodo filtrado."
        ),
        "metodo": (
            f"Total de {hm} mes(es) proyectado con modelo {modelo_meta_txt}; reparto por día con proporciones "
            f"del periodo (suavizado Laplace {_LAPLACE_DIA}). Semáforo proyectado usa los mismos "
            "umbrales que el bloque «Por día de la semana» (ratio vs. 14,29% uniforme)."
        ),
        "interpretacion": (
            "Compare barras observadas vs. proyectadas: días que concentran más carga futura "
            "sugieren cuándo reforzar operación en el horizonte elegido."
        ),
        "limitaciones": (
            "No proyecta serie propia por día; extrapola el patrón del periodo. "
            "No sustituye el semáforo histórico del mismo panel."
        ),
        "filtros": {
            "comuna_id": filtros.comuna_id,
            "barrio_id": filtros.barrio_id,
            "clase_incidente_id": filtros.clase_incidente_id,
        },
    }
    if mod == "media_movil":
        meta_out["ventana_meses"] = ventana_ma

    return {
        "meta": meta_out,
        "serie": serie,
    }
