"""
P08 — Categoría de carga esperada (alto / medio / bajo) por comuna o barrio.

Usa proyección de incidentes (modelo estacional por defecto) sumada en el horizonte
y clasifica por terciles entre territorios elegibles.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Literal

from .kpis import FiltrosKpi
from .predicciones_mensuales import (
    MA_VENTANA_DEFAULT,
    _build_single,
    normalize_modelo_proyeccion,
)
from .prioridad_territorial import MIN_INCIDENTES_TERRITORIO, _query_totales_territorio
from .territorio_sql import meta_filtros_dict, nota_modo_territorio

NivelTerritorio = Literal["comuna", "barrio"]


def _nivel_tercil(valor: float, p33: float, p66: float) -> str:
    if valor >= p66:
        return "alto"
    if valor >= p33:
        return "medio"
    return "bajo"


def _carga_proyectada_territorio(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
    nivel: NivelTerritorio,
    territorio_id: int,
    horizonte: int,
    modelo: str,
    excluir_covid: bool,
    ventana_ma: int = MA_VENTANA_DEFAULT,
) -> float | None:
    f = FiltrosKpi(
        comuna_id=territorio_id if nivel == "comuna" else filtros.comuna_id,
        barrio_id=territorio_id if nivel == "barrio" else None,
        clase_incidente_id=filtros.clase_incidente_id,
        modo_territorio=filtros.modo_territorio,
    )

    bloque = _build_single(
        inicio,
        fin,
        f,
        horizonte,
        modelo,  # type: ignore[arg-type]
        "incidentes",
        excluir_covid,
        ventana_ma=ventana_ma,
    )
    if bloque["meta"].get("sin_modelo"):
        return None
    return sum(float(r.get("proyectados") or 0) for r in bloque["proyeccion"])


def build_carga_esperada_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
    nivel: str = "comuna",
    horizonte_meses: int = 3,
    modelo: str = "estacional",
    excluir_covid: bool = True,
    limite: int = 20,
    ventana_ma: int = MA_VENTANA_DEFAULT,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    niv: NivelTerritorio = "barrio" if nivel == "barrio" else "comuna"
    hm = max(1, min(12, int(horizonte_meses)))
    limite = min(max(int(limite), 1), 50)
    mod = normalize_modelo_proyeccion(modelo)

    totales = _query_totales_territorio(inicio, fin, filtros, niv)
    filas: list[dict[str, Any]] = []

    for tid, t in totales.items():
        carga = _carga_proyectada_territorio(
            inicio, fin, filtros, niv, tid, hm, mod, excluir_covid, ventana_ma
        )
        if carga is None:
            continue
        row: dict[str, Any] = {
            "carga_proyectada_horizonte": round(carga, 2),
            "incidentes_periodo": t["incidentes"],
            "horizonte_meses": hm,
        }
        if niv == "comuna":
            row["comuna_id"] = tid
            row["comuna_nombre"] = t["nombre"]
        else:
            row["barrio_id"] = tid
            row["barrio_nombre"] = t["nombre"]
            row["comuna_nombre"] = t.get("comuna_nombre", "")
        filas.append(row)

    if not filas:
        return {
            "meta": {
                "fecha_inicio": inicio.isoformat(),
                "fecha_fin": fin.isoformat(),
                "nivel": niv,
                "sin_datos": True,
                "modelo_proyeccion": mod,
                "horizonte_meses": hm,
                "limitaciones": _limitaciones(),
                **_meta_carga_textos(mod, hm, niv, ventana_ma=ventana_ma),
            },
            "ranking": [],
        }

    cargas = [f["carga_proyectada_horizonte"] for f in filas]
    sorted_c = sorted(cargas)
    p33 = sorted_c[len(sorted_c) // 3]
    p66 = sorted_c[(2 * len(sorted_c)) // 3]

    filas.sort(key=lambda r: r["carga_proyectada_horizonte"], reverse=True)
    ranking: list[dict[str, Any]] = []
    for i, row in enumerate(filas[:limite], start=1):
        row["rank"] = i
        row["categoria_esperada"] = _nivel_tercil(row["carga_proyectada_horizonte"], p33, p66)
        ranking.append(row)

    meta_out: dict[str, Any] = {
        "fecha_inicio": inicio.isoformat(),
        "fecha_fin": fin.isoformat(),
        "nivel": niv,
        "sin_datos": False,
        "limite": limite,
        "horizonte_meses": hm,
        "modelo_proyeccion": mod,
        "excluir_covid": excluir_covid,
        "umbrales_categoria": {
            "alto": f"≥ {p66:.1f} incidentes proyectados",
            "medio": f"{p33:.1f} – {p66:.1f}",
            "bajo": f"< {p33:.1f}",
        },
        "limitaciones": _limitaciones(),
        "filtros": meta_filtros_dict(filtros),
        "nota_territorio": nota_modo_territorio(filtros.modo_territorio),
        **_meta_carga_textos(mod, hm, niv, p33, p66, ventana_ma=ventana_ma),
    }
    if mod == "media_movil":
        meta_out["ventana_meses"] = ventana_ma

    return {
        "meta": meta_out,
        "ranking": ranking,
    }


def _limitaciones() -> str:
    return (
        f"Proyección ilustrativa; no sustituye estudios de demanda. "
        f"Entran territorios con ≥ {MIN_INCIDENTES_TERRITORIO} incidentes en el periodo y serie mensual "
        "suficiente para ajustar el modelo."
    )


def _meta_carga_textos(
    modelo: str,
    hm: int,
    niv: NivelTerritorio,
    p33: float | None = None,
    p66: float | None = None,
    ventana_ma: int = MA_VENTANA_DEFAULT,
) -> dict[str, Any]:
    modelo_txt = modelo
    if modelo == "media_movil":
        modelo_txt = f"media móvil (ventana {ventana_ma} meses)"
    metodo = (
        f"Por cada {niv}, se proyectan incidentes mes a mes ({modelo_txt}) y se suman los próximos "
        f"{hm} mes(es). La categoría alto/medio/bajo compara ese total entre territorios del ranking "
        "(terciles, no umbrales fijos de la ciudad)."
    )
    interpretacion = (
        "Ordena por volumen futuro esperado de incidentes, no por gravedad (% fatales) ni por el "
        "índice compuesto del bloque P05. «Alto» significa mayor carga proyectada respecto a los "
        "demás territorios listados con los mismos filtros, no necesariamente riesgo absoluto."
    )
    if p33 is not None and p66 is not None:
        interpretacion += (
            f" Cortes de esta consulta: alto ≥ {p66:.1f} incidentes proyectados; "
            f"medio ≥ {p33:.1f}; bajo por debajo de {p33:.1f}."
        )
    return {
        "que_mide": (
            "Expectativa de incidentes agregados en el horizonte de predicción, por comuna o barrio."
        ),
        "metodo": metodo,
        "interpretacion": interpretacion,
        "lectura_columnas": {
            "carga_proyectada": f"Suma de incidentes proyectados en los próximos {hm} mes(es).",
            "categoria": "Alto / medio / bajo según terciles entre filas del ranking (relativo).",
            "incidentes_periodo": "Hechos en el rango «Desde–Hasta»; contexto del volumen histórico.",
        },
        "diferencia_p05": (
            "P05 (prioridad): mezcla frecuencia, tendencia pasada, % fatales y participación. "
            "P08: solo proyección futura de incidentes."
        ),
    }
