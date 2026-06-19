"""
Rellena el CSV de evaluación sección 3 — carga proyectada territorial (P08·P09·P10).
Uso (desde backend/):
  .venv\\Scripts\\python scripts/llenar_evaluacion_seccion3.py
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

from dashboard.carga_esperada_territorial import build_carga_esperada_payload  # noqa: E402
from dashboard.kpis import FiltrosKpi  # noqa: E402
from dashboard.prioridad_territorial import (  # noqa: E402
    _query_totales_territorio,
    build_prioridad_territorial_payload,
)

FECHA_REVISION = "2026-06-18"
CSV_PATH = BACKEND.parent / "evaluaciones" / "predicciones_seccion3_carga_territorial.csv"
LIMITE_EVAL = 50
HORIZONTE_MESES = 3
VENTANA_MA = 3

MODELOS_A = ["estacional", "ols", "media_movil", "arima", "sarima"]
MODELO_REFERENCIA = "estacional"

ESCENARIOS: dict[str, dict] = {
    "A": {
        "desc": "Ciudad completa - carga comunas (referencia)",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "nivel": "comuna",
        "comuna_id": None,
        "clase_id": None,
        "modo": "registro",
        "excluir_covid": True,
        "modelos": MODELOS_A,
    },
    "B": {
        "desc": "Ciudad completa - carga barrios",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "nivel": "barrio",
        "comuna_id": None,
        "clase_id": None,
        "modo": "registro",
        "excluir_covid": True,
        "modelos": [MODELO_REFERENCIA],
    },
    "C": {
        "desc": "Rango 12 meses - comunas",
        "desde": date(2020, 10, 1),
        "hasta": date(2021, 9, 30),
        "nivel": "comuna",
        "comuna_id": None,
        "clase_id": None,
        "modo": "registro",
        "excluir_covid": True,
        "modelos": [MODELO_REFERENCIA],
    },
    "D": {
        "desc": "Comuna Castilla - barrios",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "nivel": "barrio",
        "comuna_id": "CASTILLA",
        "clase_id": None,
        "modo": "registro",
        "excluir_covid": True,
        "modelos": [MODELO_REFERENCIA],
    },
    "E": {
        "desc": "Clase Atropello - comunas",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "nivel": "comuna",
        "comuna_id": None,
        "clase_id": "ATROPELLO",
        "modo": "registro",
        "excluir_covid": True,
        "modelos": [MODELO_REFERENCIA],
    },
    "F": {
        "desc": "Sin excluir COVID en proyección - comunas",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "nivel": "comuna",
        "comuna_id": None,
        "clase_id": None,
        "modo": "registro",
        "excluir_covid": False,
        "modelos": [MODELO_REFERENCIA],
    },
    "G": {
        "desc": "Modo territorio espacial PostGIS - comunas",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "nivel": "comuna",
        "comuna_id": None,
        "clase_id": None,
        "modo": "espacial",
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


def _nombre_territorio(row: dict, nivel: str) -> str:
    if nivel == "comuna":
        return str(row.get("comuna_nombre") or "")
    barrio = str(row.get("barrio_nombre") or "")
    comuna = str(row.get("comuna_nombre") or "")
    return f"{barrio} ({comuna})" if comuna else barrio


def _territorio_id(row: dict, nivel: str) -> int:
    return int(row["comuna_id"] if nivel == "comuna" else row["barrio_id"])


def _spearman(rank_a: dict[int, int], rank_b: dict[int, int]) -> float | None:
    common = [k for k in rank_a if k in rank_b]
    n = len(common)
    if n < 3:
        return None
    d2 = sum((rank_a[k] - rank_b[k]) ** 2 for k in common)
    return 1.0 - (6.0 * d2) / (n * (n * n - 1))


def _ranking_completo(
    cfg: dict,
    modelo: str,
) -> tuple[dict, list[dict], list[dict], dict]:
    filtros = _build_filtros(cfg)
    payload = build_carga_esperada_payload(
        cfg["desde"],
        cfg["hasta"],
        filtros,
        nivel=cfg["nivel"],
        horizonte_meses=HORIZONTE_MESES,
        modelo=modelo,
        excluir_covid=cfg["excluir_covid"],
        limite=999,
        ventana_ma=VENTANA_MA,
    )
    totales = _query_totales_territorio(cfg["desde"], cfg["hasta"], filtros, cfg["nivel"])
    ranking_full = payload.get("ranking") or []
    ranking_eval = ranking_full[:LIMITE_EVAL]
    return payload["meta"], ranking_eval, ranking_full, totales


def _analizar_carga(ranking: list[dict], nivel: str) -> dict:
    if not ranking:
        return {
            "top1_nombre": "",
            "top1_carga": "",
            "top1_categoria": "",
            "top1_incidentes": "",
            "top1_rank_frecuencia": "",
            "top3_nombres": "",
            "overlap_top5": "",
            "spearman_carga_frecuencia": "",
            "ranking_coherente": "no",
        }

    by_freq = sorted(ranking, key=lambda r: r["incidentes_periodo"], reverse=True)
    freq_rank: dict[int, int] = {_territorio_id(r, nivel): i + 1 for i, r in enumerate(by_freq)}
    carga_rank: dict[int, int] = {_territorio_id(r, nivel): r["rank"] for r in ranking}

    top1 = ranking[0]
    tid1 = _territorio_id(top1, nivel)
    top3 = "; ".join(_nombre_territorio(r, nivel) for r in ranking[:3])

    top5_carga = {_territorio_id(r, nivel) for r in ranking[:5]}
    top5_freq = {_territorio_id(r, nivel) for r in by_freq[:5]}
    overlap = len(top5_carga & top5_freq)

    sp = _spearman(carga_rank, freq_rank)

    ranking_coherente = "no"
    if sp is not None:
        if sp >= 0.75 and freq_rank.get(tid1, 99) <= 3 and overlap >= 3:
            ranking_coherente = "si"
        elif sp >= 0.5 or overlap >= 2 or freq_rank.get(tid1, 99) <= 5:
            ranking_coherente = "parcial"

    return {
        "top1_nombre": _nombre_territorio(top1, nivel),
        "top1_carga": _fmt_num(top1["carga_proyectada_horizonte"]),
        "top1_categoria": top1.get("categoria_esperada", ""),
        "top1_incidentes": str(top1["incidentes_periodo"]),
        "top1_rank_frecuencia": str(freq_rank.get(tid1, "")),
        "top3_nombres": top3,
        "overlap_top5": str(overlap),
        "spearman_carga_frecuencia": _fmt_num(round(sp, 4)) if sp is not None else "",
        "ranking_coherente": ranking_coherente,
    }


def _spearman_carga_p05(ranking_carga: list[dict], ranking_p05: list[dict], nivel: str) -> str:
    if not ranking_carga or not ranking_p05:
        return ""
    carga_rank = {_territorio_id(r, nivel): r["rank"] for r in ranking_carga}
    p05_rank = {_territorio_id(r, nivel): r["rank"] for r in ranking_p05}
    sp = _spearman(carga_rank, p05_rank)
    return _fmt_num(round(sp, 4)) if sp is not None else ""


def _overlap_top3(ids_ref: set[int], ranking: list[dict], nivel: str) -> str:
    if not ids_ref or not ranking:
        return ""
    top3 = {_territorio_id(r, nivel) for r in ranking[:3]}
    return str(len(ids_ref & top3))


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


def _p05_top1_nombre(cfg: dict) -> str:
    filtros = _build_filtros(cfg)
    p05 = build_prioridad_territorial_payload(
        cfg["desde"],
        cfg["hasta"],
        filtros,
        nivel=cfg["nivel"],
        limite=LIMITE_EVAL,
        excluir_covid=cfg["excluir_covid"],
    )
    ranking = p05.get("ranking") or []
    if not ranking:
        return ""
    return _nombre_territorio(ranking[0], cfg["nivel"])


def _cierre_util(
    ranking_coherente: str,
    nivel_ranking: str | None,
    esc_id: str,
    nivel: str,
) -> str:
    if ranking_coherente == "no" or nivel_ranking == "bajo":
        return "no"
    if esc_id == "B" and nivel == "barrio":
        return "parcial"
    if ranking_coherente == "parcial" or nivel_ranking == "moderado":
        return "parcial"
    return "si"


def _fila(
    esc_id: str,
    cfg: dict,
    modelo: str,
    ref_top3_ids: set[int] | None = None,
    ref_p05_top1: str | None = None,
) -> dict[str, str]:
    meta, ranking, ranking_full, totales = _ranking_completo(cfg, modelo)
    analisis = _analizar_carga(ranking_full, cfg["nivel"])
    bondad = meta.get("bondad_agregada") or {}

    proyectables = len(ranking_full)
    if meta.get("sin_datos"):
        proyectables = 0

    total_periodo = sum(t["incidentes"] for t in totales.values())
    territorios_totales = len(totales)

    spearman_p05 = ""
    top1_coincide_p05 = ""
    if esc_id == "A" and modelo == MODELO_REFERENCIA:
        filtros = _build_filtros(cfg)
        p05 = build_prioridad_territorial_payload(
            cfg["desde"],
            cfg["hasta"],
            filtros,
            nivel=cfg["nivel"],
            limite=LIMITE_EVAL,
            excluir_covid=cfg["excluir_covid"],
        )
        p05_ranking = p05.get("ranking") or []
        spearman_p05 = _spearman_carga_p05(ranking_full, p05_ranking, cfg["nivel"])
    if ref_p05_top1 and analisis["top1_nombre"]:
        top1_coincide_p05 = "si" if ref_p05_top1 == analisis["top1_nombre"] else "no"

    overlap_ref = ""
    if ref_top3_ids is not None and modelo != MODELO_REFERENCIA:
        overlap_ref = _overlap_top3(ref_top3_ids, ranking_full, cfg["nivel"])

    nivel_ranking = bondad.get("nivel_confianza_ranking") or ""
    nivel_cifras = bondad.get("nivel_confianza_cifras") or ""

    comuna_csv = ""
    if cfg.get("comuna_id") == "CASTILLA":
        comuna_csv = str(_build_filtros(cfg).comuna_id or "")
    clase_csv = ""
    if cfg.get("clase_id") == "ATROPELLO":
        clase_csv = str(_build_filtros(cfg).clase_incidente_id or "")

    notas = ""
    if meta.get("sin_datos"):
        notas = "Sin territorios con proyección (serie insuficiente o sin mínimos)"
    elif territorios_totales > proyectables:
        notas = f"{territorios_totales - proyectables} territorio(s) sin modelo en este ajuste"
    if esc_id == "A" and modelo != MODELO_REFERENCIA and overlap_ref == "0":
        notas = (notas + "; " if notas else "") + "Top 3 distinto al estacional"

    overlap = analisis.pop("overlap_top5")
    spearman = analisis.pop("spearman_carga_frecuencia")
    ranking_coherente = analisis.pop("ranking_coherente")
    cierre_util = _cierre_util(ranking_coherente, nivel_ranking or None, esc_id, cfg["nivel"])

    return {
        "seccion": "3_carga_territorial",
        "escenario_id": esc_id,
        "escenario_descripcion": cfg["desc"],
        "fecha_desde": cfg["desde"].strftime("%d/%m/%Y"),
        "fecha_hasta": cfg["hasta"].strftime("%d/%m/%Y"),
        "nivel": cfg["nivel"],
        "comuna_id": comuna_csv,
        "clase_incidente_id": clase_csv,
        "modo_territorio": cfg.get("modo", "registro"),
        "excluir_covid": "si" if cfg["excluir_covid"] else "no",
        "horizonte_meses": str(HORIZONTE_MESES),
        "ventana_ma": str(VENTANA_MA) if modelo == "media_movil" else "",
        "modelo": modelo,
        "sin_datos": "si" if meta.get("sin_datos") else "no",
        "territorios_totales_periodo": str(territorios_totales),
        "territorios_proyectables": str(proyectables),
        **analisis,
        "overlap_top5_carga_frecuencia": overlap,
        "spearman_carga_frecuencia": spearman,
        "spearman_carga_indice_p05": spearman_p05,
        "top1_coincide_p05": top1_coincide_p05,
        "overlap_top3_con_estacional": overlap_ref,
        "ranking_coherente": ranking_coherente,
        "nivel_confianza_ranking": nivel_ranking,
        "nivel_confianza_cifras": nivel_cifras,
        "mediana_mape_holdout_pct": _fmt_num(bondad.get("mediana_mape_holdout_pct")),
        "mape_ponderado_incidentes_pct": _fmt_num(bondad.get("mape_ponderado_incidentes_pct")),
        "mediana_mape_nucleo_pct": _fmt_num(bondad.get("mediana_mape_nucleo_pct")),
        "pct_territorios_holdout_aceptable": _fmt_num(bondad.get("pct_territorios_holdout_aceptable")),
        "cierre_util": cierre_util,
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
        "nivel",
        "comuna_id",
        "clase_incidente_id",
        "modo_territorio",
        "excluir_covid",
        "horizonte_meses",
        "ventana_ma",
        "modelo",
        "sin_datos",
        "territorios_totales_periodo",
        "territorios_proyectables",
        "top1_nombre",
        "top1_carga",
        "top1_categoria",
        "top1_incidentes",
        "top1_rank_frecuencia",
        "top3_nombres",
        "overlap_top5_carga_frecuencia",
        "spearman_carga_frecuencia",
        "spearman_carga_indice_p05",
        "top1_coincide_p05",
        "overlap_top3_con_estacional",
        "ranking_coherente",
        "nivel_confianza_ranking",
        "nivel_confianza_cifras",
        "mediana_mape_holdout_pct",
        "mape_ponderado_incidentes_pct",
        "mediana_mape_nucleo_pct",
        "pct_territorios_holdout_aceptable",
        "cierre_util",
        "notas",
        "fecha_revision",
    ]

    filas: list[dict[str, str]] = []
    ref_top3_a: set[int] = set()
    ref_p05_top1 = _p05_top1_nombre(ESCENARIOS["A"]) if "A" in ESCENARIOS else None

    for esc_id, cfg in ESCENARIOS.items():
        for modelo in cfg["modelos"]:
            fila = _fila(
                esc_id,
                cfg,
                modelo,
                ref_top3_ids=ref_top3_a if esc_id == "A" and modelo != MODELO_REFERENCIA else None,
                ref_p05_top1=ref_p05_top1 if esc_id == "A" else None,
            )
            filas.append(fila)
            if esc_id == "A" and modelo == MODELO_REFERENCIA:
                _, _, ranking_ref, _ = _ranking_completo(cfg, MODELO_REFERENCIA)
                ref_top3_a = {_territorio_id(r, cfg["nivel"]) for r in ranking_ref[:3]}

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)

    print(f"Escrito {len(filas)} filas en {CSV_PATH}")
    for row in filas:
        print(
            f"  {row['escenario_id']}/{row['modelo']}: top1={row['top1_nombre'][:36]} "
            f"util={row['cierre_util']} rank={row['nivel_confianza_ranking']} "
            f"cifras={row['nivel_confianza_cifras']} sp={row['spearman_carga_frecuencia']}"
        )


if __name__ == "__main__":
    main()
