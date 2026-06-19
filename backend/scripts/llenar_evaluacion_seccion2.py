"""
Rellena el CSV de evaluación sección 2 — prioridad territorial (P05).
Uso (desde backend/):
  .venv\\Scripts\\python scripts/llenar_evaluacion_seccion2.py
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
from dashboard.prioridad_territorial import build_prioridad_territorial_payload  # noqa: E402

FECHA_REVISION = "2026-06-18"
CSV_PATH = BACKEND.parent / "evaluaciones" / "predicciones_seccion2_prioridad_territorial.csv"
LIMITE_EVAL = 50

ESCENARIOS: dict[str, dict] = {
    "A": {
        "desc": "Ciudad completa - ranking comunas (referencia)",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "nivel": "comuna",
        "comuna_id": None,
        "clase_id": None,
        "modo": "registro",
        "excluir_covid": True,
    },
    "B": {
        "desc": "Ciudad completa - ranking barrios",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "nivel": "barrio",
        "comuna_id": None,
        "clase_id": None,
        "modo": "registro",
        "excluir_covid": True,
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
    },
    "F": {
        "desc": "Sin excluir COVID en tendencia - comunas",
        "desde": date(2018, 1, 1),
        "hasta": date(2021, 9, 30),
        "nivel": "comuna",
        "comuna_id": None,
        "clase_id": None,
        "modo": "registro",
        "excluir_covid": False,
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


def _spearman(rank_a: dict[int, int], rank_b: dict[int, int]) -> float | None:
    common = [k for k in rank_a if k in rank_b]
    n = len(common)
    if n < 3:
        return None
    d2 = sum((rank_a[k] - rank_b[k]) ** 2 for k in common)
    return 1.0 - (6.0 * d2) / (n * (n * n - 1))


def _territorio_id(row: dict, nivel: str) -> int:
    return int(row["comuna_id"] if nivel == "comuna" else row["barrio_id"])


def _analizar_ranking(ranking: list[dict], nivel: str) -> dict:
    if not ranking:
        return {
            "top1_nombre": "",
            "top1_indice": "",
            "top1_incidentes": "",
            "top1_nivel": "",
            "top1_rank_frecuencia": "",
            "top3_nombres": "",
            "overlap_top5": "",
            "spearman": "",
            "ranking_util": "no",
        }

    by_freq = sorted(ranking, key=lambda r: r["incidentes_periodo"], reverse=True)
    freq_rank: dict[int, int] = {_territorio_id(r, nivel): i + 1 for i, r in enumerate(by_freq)}
    index_rank: dict[int, int] = {_territorio_id(r, nivel): r["rank"] for r in ranking}

    top1 = ranking[0]
    tid1 = _territorio_id(top1, nivel)
    top3 = "; ".join(_nombre_territorio(r, nivel) for r in ranking[:3])

    top5_idx = {_territorio_id(r, nivel) for r in ranking[:5]}
    top5_freq = {_territorio_id(r, nivel) for r in by_freq[:5]}
    overlap = len(top5_idx & top5_freq)

    sp = _spearman(index_rank, freq_rank)

    ranking_util = "no"
    if sp is not None:
        if sp >= 0.75 and freq_rank.get(tid1, 99) <= 3 and overlap >= 3:
            ranking_util = "si"
        elif sp >= 0.5 or overlap >= 2 or freq_rank.get(tid1, 99) <= 5:
            ranking_util = "parcial"
    elif overlap >= 3:
        ranking_util = "parcial"

    return {
        "top1_nombre": _nombre_territorio(top1, nivel),
        "top1_indice": _fmt_num(top1["indice_prioridad"]),
        "top1_incidentes": str(top1["incidentes_periodo"]),
        "top1_nivel": top1["nivel_prioridad"],
        "top1_rank_frecuencia": str(freq_rank.get(tid1, "")),
        "top3_nombres": top3,
        "overlap_top5": str(overlap),
        "spearman": _fmt_num(round(sp, 4)) if sp is not None else "",
        "ranking_util": ranking_util,
    }


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


def _fila_escenario(esc_id: str, cfg: dict) -> dict[str, str]:
    filtros = _build_filtros(cfg)
    payload = build_prioridad_territorial_payload(
        cfg["desde"],
        cfg["hasta"],
        filtros,
        nivel=cfg["nivel"],
        limite=LIMITE_EVAL,
        excluir_covid=cfg["excluir_covid"],
    )
    meta = payload["meta"]
    ranking = payload["ranking"] or []
    analisis = _analizar_ranking(ranking, cfg["nivel"])

    comuna_csv = ""
    if cfg.get("comuna_id") == "CASTILLA":
        comuna_csv = str(filtros.comuna_id or "")
    clase_csv = ""
    if cfg.get("clase_id") == "ATROPELLO":
        clase_csv = str(filtros.clase_incidente_id or "")

    notas = ""
    if meta.get("sin_datos"):
        notas = "Sin territorios elegibles (min 5 incidentes)"
    elif meta.get("total_territorios_elegibles", 0) > LIMITE_EVAL:
        notas = f"Spearman/overlap calculados sobre top {LIMITE_EVAL} de {meta['total_territorios_elegibles']}"

    overlap = analisis.pop("overlap_top5")
    spearman = analisis.pop("spearman")
    return {
        "seccion": "2_prioridad_territorial",
        "escenario_id": esc_id,
        "escenario_descripcion": cfg["desc"],
        "fecha_desde": cfg["desde"].strftime("%d/%m/%Y"),
        "fecha_hasta": cfg["hasta"].strftime("%d/%m/%Y"),
        "nivel": cfg["nivel"],
        "comuna_id": comuna_csv,
        "clase_incidente_id": clase_csv,
        "modo_territorio": cfg.get("modo", "registro"),
        "excluir_covid": "si" if cfg["excluir_covid"] else "no",
        "limite": str(LIMITE_EVAL),
        "total_territorios_elegibles": str(meta.get("total_territorios_elegibles", 0)),
        "total_incidentes_periodo": str(meta.get("total_incidentes_periodo", 0)),
        **analisis,
        "overlap_top5_indice_frecuencia": overlap,
        "spearman_indice_frecuencia": spearman,
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
        "limite",
        "total_territorios_elegibles",
        "total_incidentes_periodo",
        "top1_nombre",
        "top1_indice",
        "top1_incidentes",
        "top1_nivel",
        "top1_rank_frecuencia",
        "top3_nombres",
        "overlap_top5_indice_frecuencia",
        "spearman_indice_frecuencia",
        "ranking_util",
        "notas",
        "fecha_revision",
    ]
    filas = [_fila_escenario(eid, cfg) for eid, cfg in ESCENARIOS.items()]
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(filas)
    print(f"Escrito {len(filas)} filas en {CSV_PATH}")
    for row in filas:
        print(
            f"  {row['escenario_id']}: top1={row['top1_nombre'][:40]} "
            f"util={row['ranking_util']} spearman={row['spearman_indice_frecuencia']}"
        )


if __name__ == "__main__":
    main()
