"""
Evaluación dedicada del modelo μ±3σ (tres_sigma) en las secciones de Predicciones
donde aplica selector de modelo de proyección (§1, §3, §5).

Genera: evaluaciones/predicciones_tres_sigma_evaluacion.csv

Uso (desde backend/):
  .venv\\Scripts\\python scripts/llenar_evaluacion_tres_sigma.py
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

from dashboard.carga_esperada_territorial import build_carga_esperada_payload  # noqa: E402
from dashboard.kpis import FiltrosKpi  # noqa: E402
from dashboard.patrones_temporales_proyectados import (  # noqa: E402
    build_matriz_dia_hora_proyectada_payload,
)
from dashboard.predicciones_mensuales import build_predicciones_mensuales_payload  # noqa: E402

FECHA_REVISION = "2026-06-19"
CSV_PATH = BACKEND.parent / "evaluaciones" / "predicciones_tres_sigma_evaluacion.csv"
MODELO = "tres_sigma"
HORIZONTE = 3

ESCENARIOS = {
    "A": {
        "desc": "Ciudad completa (referencia 2018–2021)",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "variable": "incidentes",
        "nivel": "comuna",
        "excluir_covid": True,
    },
    "G": {
        "desc": "Rango corto 6 meses",
        "desde": date(2021, 4, 1),
        "hasta": date(2021, 9, 30),
        "variable": "incidentes",
        "nivel": "comuna",
        "excluir_covid": True,
    },
    "F": {
        "desc": "Sin excluir COVID",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "variable": "incidentes",
        "nivel": "comuna",
        "excluir_covid": False,
    },
}

FIELDNAMES = [
    "seccion",
    "bloque_ui",
    "escenario_id",
    "escenario_descripcion",
    "fecha_desde",
    "fecha_hasta",
    "modelo",
    "sin_modelo",
    "n_meses_ajuste",
    "media_historica",
    "desviacion_estandar",
    "limite_inferior_3sigma",
    "limite_superior_3sigma",
    "pct_meses_dentro_3sigma",
    "meses_fuera_3sigma",
    "mape_holdout_pct",
    "precision_estimada_pct",
    "holdout_activo",
    "evaluacion_util",
    "metrica_clave",
    "valor_metrica",
    "notas",
    "fecha_revision",
]


def _fmt(v) -> str:
    if v is None or v == "":
        return ""
    if isinstance(v, bool):
        return "si" if v else "no"
    if isinstance(v, (int, float)):
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        return s.replace(".", ",")
    return str(v)


def _eval_util(hold_activo: bool, mape_h: float | None, pct_3s: float | None, sin_modelo: bool) -> str:
    if sin_modelo or not hold_activo:
        return "no"
    if mape_h is not None and mape_h > 25:
        return "no"
    if pct_3s is not None and pct_3s >= 90 and mape_h is not None and mape_h <= 20:
        return "si"
    if mape_h is not None and mape_h <= 25:
        return "parcial"
    return "no"


def _fila_seccion1(esc_id: str, cfg: dict) -> dict:
    p = build_predicciones_mensuales_payload(
        cfg["desde"],
        cfg["hasta"],
        FiltrosKpi(modo_territorio="registro"),
        horizonte_meses=HORIZONTE,
        modelo=MODELO,
        variable=cfg["variable"],
        excluir_covid=cfg["excluir_covid"],
        holdout_meses=3,
    )
    meta = p["meta"]
    coef = meta.get("coeficientes") or {}
    hold = meta.get("holdout") or {}
    mape_h = hold.get("mape_pct") if hold.get("activo") else None
    prec = hold.get("precision_estimada_pct")
    sin = bool(meta.get("sin_modelo"))
    pct_3s = coef.get("pct_meses_dentro_3sigma")

    return {
        "seccion": "1_proyeccion_mensual",
        "bloque_ui": "1",
        "escenario_id": esc_id,
        "escenario_descripcion": cfg["desc"],
        "fecha_desde": cfg["desde"].isoformat(),
        "fecha_hasta": cfg["hasta"].isoformat(),
        "modelo": MODELO,
        "sin_modelo": _fmt(sin),
        "n_meses_ajuste": meta.get("n_meses_ajuste", ""),
        "media_historica": _fmt(coef.get("media_historica")),
        "desviacion_estandar": _fmt(coef.get("desviacion_estandar")),
        "limite_inferior_3sigma": _fmt(coef.get("limite_inferior_3sigma")),
        "limite_superior_3sigma": _fmt(coef.get("limite_superior_3sigma")),
        "pct_meses_dentro_3sigma": _fmt(pct_3s),
        "meses_fuera_3sigma": _fmt(coef.get("meses_fuera_3sigma")),
        "mape_holdout_pct": _fmt(mape_h),
        "precision_estimada_pct": _fmt(prec),
        "holdout_activo": _fmt(hold.get("activo")),
        "evaluacion_util": _eval_util(
            bool(hold.get("activo")),
            float(mape_h) if mape_h is not None else None,
            float(pct_3s) if pct_3s is not None else None,
            sin,
        ),
        "metrica_clave": "mape_holdout_pct",
        "valor_metrica": _fmt(mape_h),
        "notas": (coef.get("interpretacion_bondad") or "")[:220],
        "fecha_revision": FECHA_REVISION,
    }


def _fila_seccion3(esc_id: str, cfg: dict) -> dict:
    p = build_carga_esperada_payload(
        cfg["desde"],
        cfg["hasta"],
        FiltrosKpi(modo_territorio="registro"),
        nivel=cfg["nivel"],
        horizonte_meses=HORIZONTE,
        modelo=MODELO,
        excluir_covid=cfg["excluir_covid"],
        limite=50,
    )
    meta = p["meta"]
    bondad = meta.get("bondad_agregada") or {}
    ranking = p.get("ranking") or []
    top1 = ranking[0]["comuna_nombre"] if ranking else ""
    spearman = bondad.get("spearman_carga_frecuencia")
    cierre = bondad.get("cierre_util") or bondad.get("nivel_confianza_ranking")

    return {
        "seccion": "3_carga_territorial",
        "bloque_ui": "3",
        "escenario_id": esc_id,
        "escenario_descripcion": cfg["desc"],
        "fecha_desde": cfg["desde"].isoformat(),
        "fecha_hasta": cfg["hasta"].isoformat(),
        "modelo": MODELO,
        "sin_modelo": _fmt(meta.get("sin_datos")),
        "n_meses_ajuste": "",
        "media_historica": "",
        "desviacion_estandar": "",
        "limite_inferior_3sigma": "",
        "limite_superior_3sigma": "",
        "pct_meses_dentro_3sigma": "",
        "meses_fuera_3sigma": "",
        "mape_holdout_pct": _fmt(bondad.get("mediana_mape_holdout_pct")),
        "precision_estimada_pct": "",
        "holdout_activo": "",
        "evaluacion_util": cierre or "parcial",
        "metrica_clave": "spearman_carga_frecuencia",
        "valor_metrica": _fmt(spearman),
        "notas": f"Top1 carga: {top1}; MAPE mediano {bondad.get('mediana_mape_holdout_pct')}"[:220],
        "fecha_revision": FECHA_REVISION,
    }


def _fila_seccion5(esc_id: str, cfg: dict) -> dict:
    filtros = FiltrosKpi(modo_territorio="registro")
    mat = build_matriz_dia_hora_proyectada_payload(
        cfg["desde"],
        cfg["hasta"],
        filtros,
        horizonte_meses=HORIZONTE,
        modelo=MODELO,
        excluir_covid=cfg["excluir_covid"],
    )
    meta = mat["meta"]
    pm = meta.get("prediccion_mensual") or {}
    sin_modelo = bool(pm.get("sin_modelo"))
    serie = mat.get("serie") or []
    top_celda = ""
    if serie:
        top = max(serie, key=lambda c: c.get("incidentes_proyectados_horizonte") or 0)
        from dashboard.por_dia_semana import _DIA_LABEL  # noqa: WPS433

        top_celda = f"{_DIA_LABEL[top['dia_semana']]} {top['hora']:02d}:00"

    p1 = build_predicciones_mensuales_payload(
        cfg["desde"],
        cfg["hasta"],
        filtros,
        horizonte_meses=HORIZONTE,
        modelo=MODELO,
        excluir_covid=cfg["excluir_covid"],
    )
    coef = (p1.get("meta") or {}).get("coeficientes") or {}

    return {
        "seccion": "5_patrones_temporales",
        "bloque_ui": "5",
        "escenario_id": esc_id,
        "escenario_descripcion": cfg["desc"],
        "fecha_desde": cfg["desde"].isoformat(),
        "fecha_hasta": cfg["hasta"].isoformat(),
        "modelo": MODELO,
        "sin_modelo": _fmt(sin_modelo),
        "n_meses_ajuste": p1["meta"].get("n_meses_ajuste", ""),
        "media_historica": _fmt(coef.get("media_historica")),
        "desviacion_estandar": _fmt(coef.get("desviacion_estandar")),
        "limite_inferior_3sigma": _fmt(coef.get("limite_inferior_3sigma")),
        "limite_superior_3sigma": _fmt(coef.get("limite_superior_3sigma")),
        "pct_meses_dentro_3sigma": _fmt(coef.get("pct_meses_dentro_3sigma")),
        "meses_fuera_3sigma": _fmt(coef.get("meses_fuera_3sigma")),
        "mape_holdout_pct": "",
        "precision_estimada_pct": "",
        "holdout_activo": "",
        "evaluacion_util": "si" if not sin_modelo else "no",
        "metrica_clave": "total_proyectado_horizonte",
        "valor_metrica": _fmt(meta.get("total_proyectado_horizonte")),
        "notas": f"P12 líder: {top_celda}"[:220],
        "fecha_revision": FECHA_REVISION,
    }


def main():
    filas: list[dict] = []
    for esc_id, cfg in ESCENARIOS.items():
        print(f"§1 {esc_id}...")
        filas.append(_fila_seccion1(esc_id, cfg))
        print(f"§3 {esc_id}...")
        filas.append(_fila_seccion3(esc_id, cfg))
        print(f"§5 {esc_id}...")
        filas.append(_fila_seccion5(esc_id, cfg))

    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES, delimiter=";", lineterminator="\n")
        writer.writeheader()
        writer.writerows(filas)

    print(f"CSV tres_sigma: {CSV_PATH} ({len(filas)} filas)")


if __name__ == "__main__":
    main()
