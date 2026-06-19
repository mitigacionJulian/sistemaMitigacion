"""
Rellena escenarios B–F del CSV de evaluación sección 1 (proyección mensual).
Uso: python manage.py shell < scripts/llenar_evaluacion_seccion1.py
O desde backend/: .venv\\Scripts\\python scripts/llenar_evaluacion_seccion1.py (con DJANGO_SETTINGS_MODULE)
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
from dashboard.predicciones_mensuales import build_predicciones_mensuales_payload  # noqa: E402

MODELOS = ["ols", "estacional", "poisson", "media_movil", "arima", "sarima"]
FECHA_REVISION = "2026-06-18"

ESCENARIOS = {
    "B": {
        "desc": "Ciudad completa - victimas",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "variable": "victimas",
        "comuna_id": None,
        "clase_id": None,
        "excluir_covid": True,
    },
    "C": {
        "desc": "Ciudad completa - victimas fatales",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "variable": "victimas_fatales",
        "comuna_id": None,
        "clase_id": None,
        "excluir_covid": True,
    },
    "D": {
        "desc": "Comuna Castilla - incidentes",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "variable": "incidentes",
        "comuna_id": "CASTILLA",
        "clase_id": None,
        "excluir_covid": True,
    },
    "E": {
        "desc": "Clase Atropello - incidentes",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "variable": "incidentes",
        "comuna_id": None,
        "clase_id": "ATROPELLO",
        "excluir_covid": True,
    },
    "F": {
        "desc": "Ciudad completa - incidentes sin excluir COVID",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "variable": "incidentes",
        "comuna_id": None,
        "clase_id": None,
        "excluir_covid": False,
    },
}


def _lookup_id(tabla: str, nombre_ilike: str) -> int:
    with connection.cursor() as c:
        c.execute(f"SELECT id, nombre FROM {tabla} WHERE nombre ILIKE %s ORDER BY id", [nombre_ilike])
        rows = c.fetchall()
    if not rows:
        raise SystemExit(f"No se encontró {nombre_ilike} en {tabla}")
    if len(rows) > 1:
        print(f"Varios matches en {tabla} para {nombre_ilike}: {rows}; usando id={rows[0][0]}")
    return int(rows[0][0])


def _fmt_num(v) -> str:
    if v is None:
        return ""
    if isinstance(v, (int, float)):
        s = f"{v:.4f}".rstrip("0").rstrip(".")
        return s.replace(".", ",")
    return str(v)


def _proyeccion_razonable(
    esc_id: str,
    sin_modelo: bool,
    hold_activo: bool,
    mape_hold: float | None,
    mape_in: float | None,
    r2: float | None,
) -> str:
    if sin_modelo or not hold_activo:
        return "no"
    if mape_hold is None:
        return "no"
    if mape_hold > 25:
        return "no"
    if esc_id == "G":
        return "parcial" if mape_hold <= 25 else "no"
    if esc_id == "I" and r2 is not None and r2 >= 0.99:
        return "parcial"
    if mape_hold <= 20:
        if mape_hold <= 15:
            return "si"
        if r2 is not None and r2 < 0.15:
            return "parcial"
        return "si"
    return "parcial"


def _nota_auto(
    esc: str,
    modelo: str,
    meta: dict,
    coef: dict | None,
    hold: dict | None,
) -> str:
    if meta.get("sin_modelo"):
        return meta.get("limitaciones", "sin modelo")[:120]
    parts = []
    mape_h = hold.get("mape_pct") if hold and hold.get("activo") else None
    if mape_h is not None:
        prec = round(100 - float(mape_h), 1)
        parts.append(f"hold-out MAPE {mape_h}% (~{prec}% prec)")
    r2 = coef.get("r2") if coef else None
    if r2 is not None and float(r2) >= 0.55:
        parts.append("buen in-sample")
    elif r2 is not None and float(r2) < 0.35:
        parts.append("R2 bajo in-sample")
    if esc == "F":
        parts.append("COVID incluido en ajuste")
    if esc == "D":
        parts.append("serie territorial Castilla")
    if esc == "E":
        parts.append("solo atropellos")
    if not hold or not hold.get("activo"):
        parts.append(hold.get("motivo", "hold-out inactivo") if hold else "sin hold-out")
    return "; ".join(parts)[:200]


def evaluar_fila(esc_id: str, cfg: dict, modelo: str, comuna_id: int | None, clase_id: int | None) -> dict:
    filtros = FiltrosKpi(
        comuna_id=comuna_id,
        clase_incidente_id=clase_id,
        modo_territorio="registro",
    )
    p = build_predicciones_mensuales_payload(
        cfg["desde"],
        cfg["hasta"],
        filtros,
        horizonte_meses=3,
        modelo=modelo,
        variable=cfg["variable"],
        excluir_covid=cfg["excluir_covid"],
        holdout_meses=3,
        evaluar_holdout=True,
    )
    meta = p["meta"]
    coef = meta.get("coeficientes") or {}
    hold = meta.get("holdout") or {}
    sin = bool(meta.get("sin_modelo"))
    mape_hold = hold.get("mape_pct") if hold.get("activo") else None

    return {
        "seccion": "1_proyeccion_mensual",
        "escenario_id": esc_id,
        "escenario_descripcion": cfg["desc"],
        "fecha_desde": cfg["desde"].strftime("%Y-%m-%d"),
        "fecha_hasta": cfg["hasta"].strftime("%Y-%m-%d"),
        "variable": cfg["variable"],
        "comuna_id": comuna_id or "",
        "clase_incidente_id": clase_id or "",
        "modo_territorio": "registro",
        "excluir_covid": "si" if cfg["excluir_covid"] else "no",
        "horizonte_meses": 3,
        "holdout_meses": 3,
        "modelo": modelo,
        "sin_modelo": "si" if sin else "no",
        "n_meses_ajuste": meta.get("n_meses_ajuste", ""),
        "r2": _fmt_num(coef.get("r2")),
        "rmse": _fmt_num(coef.get("rmse")),
        "mape_pct": _fmt_num(coef.get("mape_pct")),
        "aic": _fmt_num(coef.get("aic")),
        "bic": _fmt_num(coef.get("bic")),
        "bondad_nivel": coef.get("bondad_nivel") or meta.get("bondad_nivel") or "",
        "r2_holdout": _fmt_num(hold.get("r2")) if hold.get("activo") else "",
        "rmse_holdout": _fmt_num(hold.get("rmse")) if hold.get("activo") else "",
        "mape_holdout_pct": _fmt_num(mape_hold),
        "bondad_holdout": hold.get("bondad_nivel") or "" if hold.get("activo") else "",
        "holdout_activo": "si" if hold.get("activo") else "no",
        "proyeccion_razonable": _proyeccion_razonable(
            esc_id,
            sin,
            bool(hold.get("activo")),
            float(mape_hold) if mape_hold is not None else None,
            float(coef.get("mape_pct")) if coef.get("mape_pct") is not None else None,
            float(coef.get("r2")) if coef.get("r2") is not None else None,
        ),
        "notas": _nota_auto(esc_id, modelo, meta, coef, hold),
        "fecha_revision": FECHA_REVISION,
    }


def main():
    castilla_id = _lookup_id("comuna", "%castilla%")
    atropello_id = _lookup_id("clase_incidente", "%atropello%")
    print(f"Castilla comuna_id={castilla_id}, Atropello clase_id={atropello_id}")

    nuevas_filas = []
    for esc_id, cfg in ESCENARIOS.items():
        comuna_id = castilla_id if cfg.get("comuna_id") == "CASTILLA" else None
        clase_id = atropello_id if cfg.get("clase_id") == "ATROPELLO" else None
        for modelo in MODELOS:
            print(f"Evaluando {esc_id} / {modelo}...")
            nuevas_filas.append(evaluar_fila(esc_id, cfg, modelo, comuna_id, clase_id))

    csv_path = BACKEND.parent / "evaluaciones" / "predicciones_seccion1_proyeccion_mensual.csv"
    fieldnames = list(nuevas_filas[0].keys())

    # Leer filas existentes A, G, H, I (primeras 25 líneas de datos)
    existentes = []
    if csv_path.exists():
        with csv_path.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter=";")
            for row in reader:
                eid = (row.get("escenario_id") or "").strip()
                if eid in ("A", "G", "H", "I"):
                    existentes.append(row)

    # Normalizar filas existentes a fieldnames
    out_rows = []
    for row in existentes:
        out_rows.append({k: row.get(k, "") for k in fieldnames})
    out_rows.extend(nuevas_filas)

    # Orden: A, G, H, I, B, C, D, E, F
    orden = {"A": 0, "G": 1, "H": 2, "I": 3, "B": 4, "C": 5, "D": 6, "E": 7, "F": 8}
    modelo_ord = {m: i for i, m in enumerate(MODELOS)}
    out_rows.sort(key=lambda r: (orden.get(r["escenario_id"], 99), modelo_ord.get(r["modelo"], 99)))

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";", lineterminator="\n")
        writer.writeheader()
        writer.writerows(out_rows)

    print(f"CSV actualizado: {csv_path} ({len(out_rows)} filas)")


if __name__ == "__main__":
    main()
