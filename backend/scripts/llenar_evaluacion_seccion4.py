"""
Rellena el CSV de evaluación sección 4 — proporción víctimas fatales mensual (P07).
Uso (desde backend/):
  .venv\\Scripts\\python scripts/llenar_evaluacion_seccion4.py
"""
from __future__ import annotations

import csv
import os
import sys
from datetime import date
from pathlib import Path

import django

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.db import connection  # noqa: E402

from dashboard.kpis import FiltrosKpi  # noqa: E402
from dashboard.proporcion_fatales_mensual import build_proporcion_fatales_payload  # noqa: E402

FECHA_REVISION = "2026-06-18"
CSV_PATH = BACKEND.parent / "evaluaciones" / "predicciones_seccion4_proporcion_fatales.csv"
HORIZONTE_MESES = 3
VENTANA_MA = 3

MODELOS_A = [
    "estacional",
    "logit_offset",
    "ratio_compuesto",
    "media_movil",
    "ols",
    "logistica",
    "arima",
    "sarima",
]
MODELO_REFERENCIA = "estacional"

ESCENARIOS: dict[str, dict] = {
    "A": {
        "desc": "Ciudad completa - % fatales mensual (referencia)",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "comuna_id": None,
        "clase_id": None,
        "modo": "registro",
        "excluir_covid": True,
        "modelos": MODELOS_A,
    },
    "B": {
        "desc": "Comuna Castilla - % fatales",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "comuna_id": "CASTILLA",
        "clase_id": None,
        "modo": "registro",
        "excluir_covid": True,
        "modelos": [MODELO_REFERENCIA],
    },
    "C": {
        "desc": "Clase Atropello - % fatales",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "comuna_id": None,
        "clase_id": "ATROPELLO",
        "modo": "registro",
        "excluir_covid": True,
        "modelos": [MODELO_REFERENCIA],
    },
    "D": {
        "desc": "Rango 12 meses - % fatales",
        "desde": date(2020, 10, 1),
        "hasta": date(2021, 9, 30),
        "comuna_id": None,
        "clase_id": None,
        "modo": "registro",
        "excluir_covid": True,
        "modelos": [MODELO_REFERENCIA],
    },
    "E": {
        "desc": "Sin excluir COVID en ajuste - % fatales",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "comuna_id": None,
        "clase_id": None,
        "modo": "registro",
        "excluir_covid": False,
        "modelos": [MODELO_REFERENCIA],
    },
    "F": {
        "desc": "Modo territorio espacial PostGIS - % fatales",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "comuna_id": None,
        "clase_id": None,
        "modo": "espacial",
        "excluir_covid": True,
        "modelos": [MODELO_REFERENCIA],
    },
    "G": {
        "desc": "18 meses post-COVID - % fatales",
        "desde": date(2020, 4, 1),
        "hasta": date(2021, 9, 30),
        "comuna_id": None,
        "clase_id": None,
        "modo": "registro",
        "excluir_covid": True,
        "modelos": [MODELO_REFERENCIA],
    },
}


def _lookup_id(tabla: str, nombre_ilike: str) -> int:
    with connection.cursor() as c:
        c.execute(f"SELECT id, nombre FROM {tabla} WHERE nombre ILIKE %s ORDER BY id", [nombre_ilike])
        rows = c.fetchall()
    if not rows:
        raise SystemExit(f"No se encontró {nombre_ilike} en {tabla}")
    return int(rows[0][0])


def _fmt_num(v: float | int | None) -> str:
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        return s.replace(".", ",")
    return str(v)


def _build_filtros(cfg: dict) -> FiltrosKpi:
    comuna_id = None
    if cfg.get("comuna_id") == "CASTILLA":
        comuna_id = _lookup_id("comuna", "%castilla%")
    clase_id = None
    if cfg.get("clase_id") == "ATROPELLO":
        clase_id = _lookup_id("clase_incidente", "%atropello%")
    return FiltrosKpi(
        comuna_id=comuna_id,
        clase_incidente_id=clase_id,
        modo_territorio=cfg.get("modo", "registro"),
    )


def _stats_serie(payload: dict) -> dict[str, str]:
    hist = payload.get("serie_historica") or []
    proj = payload.get("proyeccion") or []
    pcts_obs = [float(r["pct_fatales"]) for r in hist if r.get("pct_fatales") is not None]
    n_ajuste = sum(1 for r in hist if r.get("ajuste_pct") is not None)
    pct_prom = round(sum(pcts_obs) / len(pcts_obs), 2) if pcts_obs else None
    pct_min = round(min(pcts_obs), 2) if pcts_obs else None
    pct_max = round(max(pcts_obs), 2) if pcts_obs else None
    pct_proj = None
    if proj:
        vals = [float(r.get("pct_fatales_proyectado") or r.get("ajuste_pct") or 0) for r in proj]
        pct_proj = round(sum(vals) / len(vals), 2) if vals else None
    return {
        "n_meses_con_pct_observado": str(len(pcts_obs)),
        "n_meses_ajuste": str(n_ajuste),
        "pct_promedio_observado": _fmt_num(pct_prom),
        "pct_min_observado": _fmt_num(pct_min),
        "pct_max_observado": _fmt_num(pct_max),
        "pct_promedio_horizonte": _fmt_num(pct_proj),
    }


def _proyeccion_razonable_p07(
    sin_modelo: bool,
    r2: float | None,
    mape: float | None,
    bondad: str | None,
    modelo: str,
    esc_id: str,
    mape_holdout: float | None,
    holdout_activo: bool,
) -> str:
    if sin_modelo:
        return "no"
    if esc_id == "G" and r2 is not None and r2 >= 0.99:
        return "parcial"
    if holdout_activo and mape_holdout is not None and mape_holdout <= 20:
        if modelo in ("estacional", "logit_offset", "ratio_compuesto", "media_movil"):
            return "si"
        return "parcial"
    if bondad == "bueno":
        return "si"
    if modelo in ("estacional", "logit_offset", "ratio_compuesto") and r2 is not None and r2 >= 0.35:
        if mape is not None and mape <= 20:
            return "si"
        return "parcial"
    if modelo == "media_movil" and mape is not None and mape <= 15:
        return "parcial"
    if bondad == "moderado" and modelo in ("estacional", "logit_offset", "ratio_compuesto", "media_movil"):
        return "parcial"
    return "no"


def _fila(esc_id: str, cfg: dict, modelo: str) -> dict[str, str]:
    filtros = _build_filtros(cfg)
    payload = build_proporcion_fatales_payload(
        cfg["desde"],
        cfg["hasta"],
        filtros,
        horizonte_meses=HORIZONTE_MESES,
        modelo=modelo,
        excluir_covid=cfg["excluir_covid"],
        ventana_ma=VENTANA_MA,
        holdout_meses=3,
    )
    meta = payload["meta"]
    coef = meta.get("coeficientes") or {}
    hold = meta.get("holdout") or {}
    sin_modelo = bool(meta.get("sin_modelo"))
    r2 = float(coef["r2"]) if coef.get("r2") is not None else None
    mape = float(coef["mape_pct"]) if coef.get("mape_pct") is not None else None
    bondad = meta.get("bondad_nivel") or coef.get("bondad_nivel") or ""
    mape_hold = hold.get("mape_pct")
    mape_hold_f = float(mape_hold) if mape_hold is not None else None
    hold_activo = bool(hold.get("activo"))

    comuna_csv = ""
    if cfg.get("comuna_id") == "CASTILLA":
        comuna_csv = str(filtros.comuna_id or "")
    clase_csv = ""
    if cfg.get("clase_id") == "ATROPELLO":
        clase_csv = str(filtros.clase_incidente_id or "")

    stats = _stats_serie(payload)
    proy_ok = _proyeccion_razonable_p07(
        sin_modelo, r2, mape, bondad, modelo, esc_id, mape_hold_f, hold_activo
    )

    notas = ""
    if sin_modelo:
        notas = meta.get("interpretacion_bondad", "Sin modelo")[:120]
    elif modelo in ("ols", "logistica") and r2 is not None and r2 < 0.1:
        notas = "OLS/logit: R² ~0 habitual en % fatales volátil"
    elif modelo in ("arima", "sarima") and r2 is not None and r2 < 0.15:
        notas = "ARIMA/SARIMA: % mensual muy volátil; preferir estacional"

    return {
        "seccion": "4_proporcion_fatales",
        "escenario_id": esc_id,
        "escenario_descripcion": cfg["desc"],
        "fecha_desde": cfg["desde"].strftime("%d/%m/%Y"),
        "fecha_hasta": cfg["hasta"].strftime("%d/%m/%Y"),
        "comuna_id": comuna_csv,
        "clase_incidente_id": clase_csv,
        "modo_territorio": cfg.get("modo", "registro"),
        "excluir_covid": "si" if cfg["excluir_covid"] else "no",
        "horizonte_meses": str(HORIZONTE_MESES),
        "holdout_meses": "3",
        "ventana_ma": str(VENTANA_MA) if modelo == "media_movil" else "",
        "modelo": modelo,
        "sin_modelo": "si" if sin_modelo else "no",
        **stats,
        "r2": _fmt_num(coef.get("r2")),
        "rmse": _fmt_num(coef.get("rmse")),
        "mape_pct": _fmt_num(coef.get("mape_pct")),
        "mape_holdout_pct": _fmt_num(mape_hold),
        "holdout_activo": "si" if hold_activo else "no",
        "bondad_nivel": bondad,
        "proyeccion_razonable": proy_ok,
        "notas": notas,
        "fecha_revision": FECHA_REVISION,
    }


def main() -> None:
    fieldnames = [
        "seccion",
        "escenario_id",
        "escenario_descripcion",
        "fecha_desde",
        "fecha_hasta",
        "comuna_id",
        "clase_incidente_id",
        "modo_territorio",
        "excluir_covid",
        "horizonte_meses",
        "holdout_meses",
        "ventana_ma",
        "modelo",
        "sin_modelo",
        "n_meses_con_pct_observado",
        "n_meses_ajuste",
        "pct_promedio_observado",
        "pct_min_observado",
        "pct_max_observado",
        "pct_promedio_horizonte",
        "r2",
        "rmse",
        "mape_pct",
        "mape_holdout_pct",
        "holdout_activo",
        "bondad_nivel",
        "proyeccion_razonable",
        "notas",
        "fecha_revision",
    ]

    filas: list[dict[str, str]] = []
    for esc_id, cfg in ESCENARIOS.items():
        for modelo in cfg["modelos"]:
            filas.append(_fila(esc_id, cfg, modelo))

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)

    print(f"Escrito {len(filas)} filas en {CSV_PATH}")
    for row in filas:
        print(
            f"  {row['escenario_id']}/{row['modelo']}: r2={row['r2']} mape={row['mape_pct']} "
            f"bondad={row['bondad_nivel']} util={row['proyeccion_razonable']} "
            f"pct_obs={row['pct_promedio_observado']}"
        )


if __name__ == "__main__":
    main()
