"""
Rellena el CSV de evaluación sección 5 — patrones día×hora (P12) y día semana (P13).
Uso (desde backend/):
  .venv\\Scripts\\python scripts/llenar_evaluacion_seccion5.py
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
from dashboard.patrones_temporales_proyectados import (  # noqa: E402
    build_dia_semana_proyectado_payload,
    build_matriz_dia_hora_proyectada_payload,
)
from dashboard.por_dia_semana import _DIA_LABEL  # noqa: E402

FECHA_REVISION = "2026-06-18"
CSV_PATH = BACKEND.parent / "evaluaciones" / "predicciones_seccion5_patrones_temporales.csv"
HORIZONTE_MESES = 3
VENTANA_MA = 3
MIN_INCIDENTES_PERIODO = 100

MODELOS_A = ["estacional", "ols", "media_movil", "arima", "sarima"]
MODELO_REFERENCIA = "estacional"

ESCENARIOS: dict[str, dict] = {
    "A": {
        "desc": "Ciudad completa - patrones P12/P13 (referencia)",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "comuna_id": None,
        "clase_id": None,
        "modo": "registro",
        "excluir_covid": True,
        "modelos": MODELOS_A,
    },
    "B": {
        "desc": "Comuna Castilla - patrones",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "comuna_id": "CASTILLA",
        "clase_id": None,
        "modo": "registro",
        "excluir_covid": True,
        "modelos": [MODELO_REFERENCIA],
    },
    "C": {
        "desc": "Clase Atropello - patrones",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "comuna_id": None,
        "clase_id": "ATROPELLO",
        "modo": "registro",
        "excluir_covid": True,
        "modelos": [MODELO_REFERENCIA],
    },
    "D": {
        "desc": "Rango 12 meses - patrones",
        "desde": date(2020, 10, 1),
        "hasta": date(2021, 9, 30),
        "comuna_id": None,
        "clase_id": None,
        "modo": "registro",
        "excluir_covid": True,
        "modelos": [MODELO_REFERENCIA],
    },
    "E": {
        "desc": "Sin excluir COVID - patrones",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "comuna_id": None,
        "clase_id": None,
        "modo": "registro",
        "excluir_covid": False,
        "modelos": [MODELO_REFERENCIA],
    },
    "F": {
        "desc": "Modo territorio espacial PostGIS - patrones",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "comuna_id": None,
        "clase_id": None,
        "modo": "espacial",
        "excluir_covid": True,
        "modelos": [MODELO_REFERENCIA],
    },
    "G": {
        "desc": "18 meses post-COVID - patrones",
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


def _spearman(rank_a: dict, rank_b: dict) -> float | None:
    common = [k for k in rank_a if k in rank_b]
    n = len(common)
    if n < 3:
        return None
    d2 = sum((rank_a[k] - rank_b[k]) ** 2 for k in common)
    return 1.0 - (6.0 * d2) / (n * (n * n - 1))


def _ranks_por_valor(keys: list, valores: list) -> dict:
    orden = sorted(range(len(valores)), key=lambda i: valores[i], reverse=True)
    out: dict = {}
    for r, i in enumerate(orden, 1):
        out[keys[i]] = r
    return out


def _spearman_celdas(serie: list[dict]) -> float | None:
    keys = [(c["dia_semana"], c["hora"]) for c in serie]
    obs = [c["incidentes_observados_periodo"] for c in serie]
    proj = [c["incidentes_proyectados_horizonte"] for c in serie]
    return _spearman(_ranks_por_valor(keys, obs), _ranks_por_valor(keys, proj))


def _analizar_p12(serie: list[dict]) -> dict[str, str]:
    if not serie:
        return {
            "p12_top_celda": "",
            "p12_top_proyectados": "",
            "p12_top_participacion_pct": "",
            "p12_celdas_con_datos": "0",
            "p12_spearman_obs_proy": "",
            "p12_coherente": "no",
        }
    top = max(serie, key=lambda c: c["incidentes_proyectados_horizonte"])
    top_obs = max(serie, key=lambda c: c["incidentes_observados_periodo"])
    con_datos = sum(1 for c in serie if c["incidentes_observados_periodo"] > 0)
    sp = _spearman_celdas(serie)
    misma_top = (
        top["dia_semana"] == top_obs["dia_semana"] and top["hora"] == top_obs["hora"]
    )
    return {
        "p12_top_celda": f"{_DIA_LABEL[top['dia_semana']]} {top['hora']:02d}:00",
        "p12_top_proyectados": str(top["incidentes_proyectados_horizonte"]),
        "p12_top_participacion_pct": _fmt_num(top.get("participacion_proyectada_pct")),
        "p12_celdas_con_datos": str(con_datos),
        "p12_spearman_obs_proy": _fmt_num(round(sp, 4)) if sp is not None else "",
        "p12_top_igual_obs": "si" if misma_top else "no",
        "p12_coherente": "si",
    }


def _analizar_p13(serie: list[dict]) -> dict[str, str]:
    if not serie:
        return {
            "p13_top_dia": "",
            "p13_top_proyectados": "",
            "p13_top_participacion_pct": "",
            "p13_top_igual_obs": "no",
        }
    top = max(serie, key=lambda c: c["incidentes_proyectados_horizonte"])
    top_obs = max(serie, key=lambda c: c["incidentes_observados_periodo"])
    return {
        "p13_top_dia": top["dia"],
        "p13_top_proyectados": str(top["incidentes_proyectados_horizonte"]),
        "p13_top_participacion_pct": _fmt_num(top.get("participacion_proyectada_pct")),
        "p13_top_igual_obs": "si" if top["dia_semana"] == top_obs["dia_semana"] else "no",
        "p13_top_nivel": top.get("carga_dia_nivel_proyectado", ""),
    }


def _patron_util(
    sin_datos: bool,
    sin_modelo: bool,
    total_periodo: int,
    coherente: bool,
    esc_id: str,
) -> str:
    if sin_datos or sin_modelo:
        return "no"
    if total_periodo < MIN_INCIDENTES_PERIODO:
        return "parcial"
    if esc_id in ("D", "G") and total_periodo < 500:
        return "parcial"
    if not coherente:
        return "no"
    if esc_id == "E":
        return "parcial"
    return "si"


def _fila(esc_id: str, cfg: dict, modelo: str) -> dict[str, str]:
    filtros = _build_filtros(cfg)
    mat = build_matriz_dia_hora_proyectada_payload(
        cfg["desde"],
        cfg["hasta"],
        filtros,
        horizonte_meses=HORIZONTE_MESES,
        modelo=modelo,
        excluir_covid=cfg["excluir_covid"],
        ventana_ma=VENTANA_MA,
    )
    dia = build_dia_semana_proyectado_payload(
        cfg["desde"],
        cfg["hasta"],
        filtros,
        horizonte_meses=HORIZONTE_MESES,
        modelo=modelo,
        excluir_covid=cfg["excluir_covid"],
        ventana_ma=VENTANA_MA,
    )
    meta_m = mat["meta"]
    meta_d = dia["meta"]
    pm = meta_m.get("prediccion_mensual") or {}
    sin_datos = bool(meta_m.get("sin_datos"))
    sin_modelo = bool(pm.get("sin_modelo"))
    total_periodo = int(meta_m.get("total_incidentes_periodo") or 0)
    val = meta_m.get("validacion_diferencia") or {}
    coherente = bool(val.get("coherente", False))

    p12 = _analizar_p12(mat.get("serie") or [])
    p12["p12_coherente"] = "si" if coherente else "no"
    p13 = _analizar_p13(dia.get("serie") or [])

    util = _patron_util(sin_datos, sin_modelo, total_periodo, coherente, esc_id)

    comuna_csv = ""
    if cfg.get("comuna_id") == "CASTILLA":
        comuna_csv = str(filtros.comuna_id or "")
    clase_csv = ""
    if cfg.get("clase_id") == "ATROPELLO":
        clase_csv = str(filtros.clase_incidente_id or "")

    notas = ""
    if sin_modelo:
        notas = "Sin proyección mensual; no hay reparto día×hora"
    elif total_periodo < MIN_INCIDENTES_PERIODO:
        notas = f"Pocos incidentes en periodo ({total_periodo})"
    elif modelo == "arima" and esc_id == "A":
        notas = "ARIMA cambia total proyectado; patrón relativo igual"

    return {
        "seccion": "5_patrones_temporales",
        "escenario_id": esc_id,
        "escenario_descripcion": cfg["desc"],
        "fecha_desde": cfg["desde"].strftime("%d/%m/%Y"),
        "fecha_hasta": cfg["hasta"].strftime("%d/%m/%Y"),
        "comuna_id": comuna_csv,
        "clase_incidente_id": clase_csv,
        "modo_territorio": cfg.get("modo", "registro"),
        "excluir_covid": "si" if cfg["excluir_covid"] else "no",
        "horizonte_meses": str(HORIZONTE_MESES),
        "ventana_ma": str(VENTANA_MA) if modelo == "media_movil" else "",
        "modelo": modelo,
        "sin_datos": "si" if sin_datos else "no",
        "sin_modelo_mensual": "si" if sin_modelo else "no",
        "total_incidentes_periodo": str(total_periodo),
        "total_proyectado_horizonte": _fmt_num(meta_m.get("total_proyectado_horizonte")),
        "meses_en_periodo": str(meta_m.get("meses_en_periodo") or ""),
        "r2_modelo_mensual": _fmt_num(pm.get("r2")),
        **p12,
        **p13,
        "patron_util": util,
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
        "ventana_ma",
        "modelo",
        "sin_datos",
        "sin_modelo_mensual",
        "total_incidentes_periodo",
        "total_proyectado_horizonte",
        "meses_en_periodo",
        "r2_modelo_mensual",
        "p12_top_celda",
        "p12_top_proyectados",
        "p12_top_participacion_pct",
        "p12_celdas_con_datos",
        "p12_spearman_obs_proy",
        "p12_top_igual_obs",
        "p12_coherente",
        "p13_top_dia",
        "p13_top_proyectados",
        "p13_top_participacion_pct",
        "p13_top_igual_obs",
        "p13_top_nivel",
        "patron_util",
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
            f"  {row['escenario_id']}/{row['modelo']}: util={row['patron_util']} "
            f"total_p={row['total_proyectado_horizonte']} p12={row['p12_top_celda']} "
            f"p13={row['p13_top_dia']}"
        )


if __name__ == "__main__":
    main()
