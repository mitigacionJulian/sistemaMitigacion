"""
Recalcula proyeccion_razonable para escenarios A, G, H, I según métricas del CSV.
Criterio:
  - no: sin modelo, hold-out inactivo, o MAPE hold-out > 25 %
  - si: hold-out activo, MAPE ≤ 20 %, sin banderas de cautela fuerte
  - parcial: resto de casos con hold-out activo, o serie muy corta (G) con MAPE ≤ 20 %
"""
from __future__ import annotations

import csv
from pathlib import Path


def _parse_num(s: str) -> float | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def proyeccion_razonable_fila(row: dict) -> str:
    esc = (row.get("escenario_id") or "").strip()
    sin = (row.get("sin_modelo") or "").strip().lower() == "si"
    hold_activo = (row.get("holdout_activo") or "").strip().lower() == "si"
    mape_h = _parse_num(row.get("mape_holdout_pct") or "")
    mape_in = _parse_num(row.get("mape_pct") or "")
    r2 = _parse_num(row.get("r2") or "")

    if sin or not hold_activo:
        return "no"
    if mape_h is None:
        return "no"
    if mape_h > 25:
        return "no"

    # G: solo 6 meses — MAPE bajo no basta para «si» pleno
    if esc == "G":
        return "parcial" if mape_h <= 25 else "no"

    # I: R² ≈ 1 con pocos meses válidos (artefacto de sobreajuste)
    if esc == "I" and r2 is not None and r2 >= 0.99:
        return "parcial"

    if mape_h <= 20:
        # MAPE hold-out claramente bueno (prioridad sobre R² bajo)
        if mape_h <= 15:
            return "si"
        if r2 is not None and r2 < 0.15:
            return "parcial"
        return "si"

    # 20 % < MAPE hold-out ≤ 25 %
    return "parcial"


def main():
    csv_path = Path(__file__).resolve().parents[2] / "evaluaciones" / "predicciones_seccion1_proyeccion_mensual.csv"
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        fieldnames = reader.fieldnames
        rows = list(reader)

    cambios = []
    for row in rows:
        esc = (row.get("escenario_id") or "").strip()
        if esc not in ("A", "G", "H", "I"):
            continue
        # Reparar filas sin modelo con columnas desalineadas
        if (row.get("sin_modelo") or "").strip().lower() == "si":
            row["proyeccion_razonable"] = "no"
            row["holdout_activo"] = "no"
            modelo = (row.get("modelo") or "").strip()
            if modelo == "arima":
                row["notas"] = "sin modelo; requiere >= 12 meses"
            elif modelo == "sarima":
                row["notas"] = "sin modelo; requiere >= 24 meses"
            else:
                row["notas"] = "sin modelo"
            row["fecha_revision"] = "2026-06-18"
            continue
        if esc == "H" and (row.get("modelo") or "") == "arima" and (row.get("holdout_activo") or "").lower() != "si":
            row["proyeccion_razonable"] = "no"
            row["notas"] = "hold-out inactivo; faltan 15 meses (12+3 hold-out)"
            row["fecha_revision"] = "2026-06-18"
            continue
        if esc == "I" and (row.get("modelo") or "") == "arima" and (row.get("holdout_activo") or "").lower() != "si":
            row["proyeccion_razonable"] = "no"
            row["notas"] = "hold-out inactivo; faltan 15 meses"
            row["fecha_revision"] = "2026-06-18"
            continue
        nuevo = proyeccion_razonable_fila(row)
        viejo = (row.get("proyeccion_razonable") or "").strip()
        if nuevo != viejo:
            cambios.append((esc, row.get("modelo"), viejo or "(vacío)", nuevo))
            row["proyeccion_razonable"] = nuevo
        if not (row.get("fecha_revision") or "").strip():
            row["fecha_revision"] = "2026-06-18"

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=";", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)

    print(f"Actualizado: {csv_path}")
    if cambios:
        print("Cambios proyeccion_razonable:")
        for esc, mod, viejo, nuevo in cambios:
            print(f"  {esc}/{mod}: {viejo} -> {nuevo}")
    else:
        print("Sin cambios (ya coherentes).")


if __name__ == "__main__":
    main()
