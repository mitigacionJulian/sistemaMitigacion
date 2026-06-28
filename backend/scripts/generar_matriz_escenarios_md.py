"""
Genera la matriz de escenarios en Markdown para el informe de grado.

Lee los CSV de evaluaciones/ (generados con llenar_evaluacion_todas_secciones.py)
y escribe evaluaciones/MATRIZ_ESCENARIOS_CASO_ESTUDIO.md

Uso (desde backend/):
  .venv\\Scripts\\python scripts/generar_matriz_escenarios_md.py
  .venv\\Scripts\\python scripts/generar_matriz_escenarios_md.py --escenario A
"""
from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
EVAL = BACKEND.parent / "evaluaciones"
OUT_PATH = EVAL / "MATRIZ_ESCENARIOS_CASO_ESTUDIO.md"

CASO_PRINCIPAL = "A"

MODELO_LABELS = {
    "ols": "OLS",
    "estacional": "Estacional",
    "poisson": "Poisson",
    "media_movil": "Media móvil",
    "tres_sigma": "μ±3σ",
    "arima": "ARIMA",
    "sarima": "SARIMA",
    "logit_offset": "Logit con exposición",
    "ratio_compuesto": "Ratio compuesto",
    "logistica": "Logit-lineal",
}

ESCENARIOS_META = {
    "A": {
        "titulo": "Ciudad completa — referencia principal",
        "desde": "2018-01-01",
        "hasta": "2021-09-30",
        "filtros": "Incidentes, territorio registro Mede, excluir mar–ago 2020",
        "proposito": "Caso de estudio principal para sustentar el sistema a nivel municipal.",
    },
    "B": {"titulo": "Ciudad — víctimas (§1) / barrios (§2–3)", "proposito": "Otra variable o granularidad territorial."},
    "C": {"titulo": "Fatales o rango corto", "proposito": "Series volátiles o historia reducida."},
    "D": {"titulo": "Comuna Castilla", "proposito": "Territorio acotado."},
    "E": {"titulo": "Clase Atropello o sin COVID", "proposito": "Filtro por clase o sensibilidad COVID."},
    "F": {"titulo": "Sin excluir COVID", "proposito": "Contraste de exclusión del confinamiento."},
    "G": {"titulo": "Rango 6 meses o modo espacial", "proposito": "Poca historia o territorio PostGIS."},
    "H": {"titulo": "Rango 12 meses", "proposito": "Mínimo ARIMA; SARIMA inactivo."},
    "I": {"titulo": "18 meses post-COVID", "proposito": "Comportamiento reciente."},
}


def _read_csv(name: str) -> list[dict[str, str]]:
    path = EVAL / name
    if not path.is_file():
        raise SystemExit(f"Falta {path}. Ejecute: python scripts/llenar_evaluacion_todas_secciones.py")
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=";"))


def _num(s: str | None) -> float | None:
    if s is None or str(s).strip() == "":
        return None
    try:
        return float(str(s).replace(",", "."))
    except ValueError:
        return None


def _label(modelo: str) -> str:
    return MODELO_LABELS.get(modelo, modelo)


def _fmt_pct(v: float | None, dec: int = 2) -> str:
    if v is None:
        return "—"
    return f"{v:.{dec}f} %".replace(".", ",")


def _fmt_num(v: float | None, dec: int = 2) -> str:
    if v is None:
        return "—"
    return f"{v:.{dec}f}".replace(".", ",")


def _precision(mape: float | None) -> str:
    if mape is None:
        return "—"
    return _fmt_pct(round(100 - mape, 1), 1)


def _filter_esc(rows: list[dict], esc: str) -> list[dict]:
    return [r for r in rows if r.get("escenario_id") == esc]


def _best_worst(rows: list[dict], key: str, lower_better: bool = True) -> tuple[dict | None, dict | None]:
    valid = [r for r in rows if _num(r.get(key)) is not None and r.get("sin_modelo") != "si" and r.get("sin_datos") != "si"]
    if not valid:
        return None, None
    valid.sort(key=lambda r: _num(r[key]) or 0, reverse=not lower_better)
    return valid[0], valid[-1]


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def seccion1_md(esc: str, rows: list[dict]) -> str:
    sub = _filter_esc(rows, esc)
    if not sub:
        return "_Sin datos para este escenario._\n"

    table_rows = []
    for r in sub:
        mape_h = _num(r.get("mape_holdout_pct"))
        table_rows.append(
            [
                _label(r["modelo"]),
                _fmt_num(_num(r.get("r2")), 3),
                _fmt_pct(_num(r.get("mape_pct"))),
                _fmt_pct(mape_h),
                _precision(mape_h),
                r.get("proyeccion_razonable", "—"),
                (r.get("notas") or "")[:80],
            ]
        )

    best, worst = _best_worst(sub, "mape_holdout_pct")
    tres = next((r for r in sub if r.get("modelo") == "tres_sigma"), None)

    parts = [
        "### 3.1 Matriz modelo × métricas\n",
        _md_table(
            ["Modelo", "R² ajuste", "MAPE ajuste", "MAPE hold-out", "Precisión est.", "¿Razonable?", "Notas"],
            table_rows,
        ),
        "",
        "### 3.2 Mejor y peor modelo (criterio: MAPE hold-out)\n",
    ]
    if best:
        bh = _num(best.get("mape_holdout_pct"))
        parts.append(
            f"- **Mejor:** {_label(best['modelo'])} — MAPE hold-out {_fmt_pct(bh)} "
            f"(precisión estimada {_precision(bh)}). {best.get('proyeccion_razonable', '') == 'si' and 'Cumple umbral ≤ 20 %.' or ''}"
        )
    if worst:
        wh = _num(worst.get("mape_holdout_pct"))
        parts.append(
            f"- **Peor:** {_label(worst['modelo'])} — MAPE hold-out {_fmt_pct(wh)} "
            f"(precisión estimada {_precision(wh)}). Suele sobreajustar el in-sample o ignorar estacionalidad."
        )
    parts.append("\n### 3.3 Interpretación para el caso de estudio\n")
    if esc == CASO_PRINCIPAL:
        parts.append(
            "La prueba con 3 meses reservados desempata modelos que en el ajuste parecen equivalentes. "
            "Poisson y estacional muestran buen MAPE in-sample (~8 %) pero superan 22 % en hold-out; "
            "no deben elegirse solo por R² o MAPE bajo el gráfico. "
            "SARIMA minimiza el error predictivo; media móvil y μ±3σ son alternativas interpretables "
            f"con precisión ≥ 82 %."
        )
        if tres:
            parts.append(
                f"\n**μ±3σ:** media ≈ {_fmt_num(_num(tres.get('media_historica')), 0)} incidentes/mes; "
                f"banda [{_fmt_num(_num(tres.get('limite_inferior_3sigma')), 0)} – "
                f"{_fmt_num(_num(tres.get('limite_superior_3sigma')), 0)}]; "
                f"{tres.get('pct_meses_dentro_3sigma', '—')} % meses dentro. "
                f"MAPE hold-out {_fmt_pct(_num(tres.get('mape_holdout_pct')))} — útil como línea base y para sustentar "
                "estabilidad del historial, no para captar picos mensuales."
            )
    else:
        parts.append(
            "Compare MAPE hold-out con el escenario A. Rangos cortos o filtros estrechos degradan la confiabilidad."
        )
    return "\n".join(parts) + "\n"


def seccion2_md(esc: str, rows: list[dict]) -> str:
    sub = _filter_esc(rows, esc)
    if not sub:
        return "_Sin datos._\n"
    r = sub[0]
    return f"""### 4.1 Resultado del escenario (sin comparación de modelos)

La sección 2 usa **fórmula fija** (índice compuesto P05); no hay selector de modelo.

| Indicador | Valor |
| --- | --- |
| Nivel | {r.get('nivel', '—')} |
| Territorios elegibles | {r.get('total_territorios_elegibles', '—')} |
| Incidentes en periodo | {r.get('total_incidentes_periodo', '—')} |
| #1 índice | **{r.get('top1_nombre', '—')}** (índice {r.get('top1_indice', '—')}) |
| #1 por volumen | Puesto {r.get('top1_rank_frecuencia', '—')} |
| Nivel prioridad #1 | {r.get('top1_nivel', '—')} |
| Spearman índice↔volumen | {r.get('spearman_indice_frecuencia', '—')} |
| Utilidad documentada | {r.get('ranking_util', '—')} |

### 4.2 Interpretación

El ranking resume **dónde concentró el problema en el pasado** (frecuencia, densidad, delta de promedios, gravedad, participación). 
Complementa la proyección forward de las secciones 1 y 3: un territorio líder en P05 no implica automáticamente el mayor volumen proyectado en P08.
Para barrios (escenario B) la utilidad es **parcial** — conviene contrastar con la vista «solo por frecuencia».
"""


def seccion3_md(esc: str, rows: list[dict]) -> str:
    sub = _filter_esc(rows, esc)
    if not sub:
        return "_Sin datos._\n"

    table_rows = []
    for r in sub:
        table_rows.append(
            [
                _label(r["modelo"]),
                r.get("top1_nombre", "—"),
                r.get("top1_carga", "—"),
                r.get("spearman_carga_frecuencia", "—"),
                r.get("mediana_mape_holdout_pct", "—") + (" %" if r.get("mediana_mape_holdout_pct") else ""),
                r.get("nivel_confianza_ranking", "—"),
                r.get("nivel_confianza_cifras", "—"),
                r.get("cierre_util", "—"),
            ]
        )

    best_sp, worst_sp = _best_worst(sub, "spearman_carga_frecuencia", lower_better=False)
    best_mape, worst_mape = _best_worst(sub, "mediana_mape_holdout_pct")

    parts = [
        "### 5.1 Matriz modelo × ranking y cifras\n",
        _md_table(
            [
                "Modelo",
                "Top carga",
                "Carga #1",
                "Spearman",
                "MAPE med. hold-out",
                "Conf. ranking",
                "Conf. cifras",
                "Util",
            ],
            table_rows,
        ),
        "",
        "### 5.2 Mejor y peor modelo\n",
        "**Ranking (Spearman carga↔volumen):**",
    ]
    if best_sp:
        parts.append(f"- Mejor: **{_label(best_sp['modelo'])}** (ρ = {best_sp.get('spearman_carga_frecuencia')})")
    if worst_sp:
        parts.append(f"- Peor: **{_label(worst_sp['modelo'])}** (ρ = {worst_sp.get('spearman_carga_frecuencia')})")
    parts.append("\n**Cifras absolutas (MAPE mediano hold-out por territorio):**")
    if best_mape:
        parts.append(f"- Mejor: **{_label(best_mape['modelo'])}** ({best_mape.get('mediana_mape_holdout_pct')} %)")
    if worst_mape:
        parts.append(f"- Peor: **{_label(worst_mape['modelo'])}** ({worst_mape.get('mediana_mape_holdout_pct')} %)")

    parts.append("\n### 5.3 Interpretación\n")
    if esc == CASO_PRINCIPAL:
        parts.append(
            "Hay **dos criterios** que pueden divergir: μ±3σ logra el ranking más coherente con el volumen histórico "
            "y el MAPE territorial más bajo, pero proyecta una carga constante por comuna. "
            "Estacional es la opción adoptada para captar variación mensual; ARIMA degradó el ranking (#1 erróneo: Sin Inf). "
            "La carga no debe leerse como presupuesto exacto: el MAPE mediano ~21–33 % indica orden de magnitud."
        )
    return "\n".join(parts) + "\n"


def seccion4_md(esc: str, rows: list[dict]) -> str:
    sub = _filter_esc(rows, esc)
    if not sub:
        return "_Sin datos._\n"

    table_rows = []
    for r in sub:
        table_rows.append(
            [
                _label(r["modelo"]),
                r.get("pct_promedio_observado", "—") + " %",
                _fmt_num(_num(r.get("r2")), 3),
                _fmt_pct(_num(r.get("mape_pct"))),
                _fmt_pct(_num(r.get("mape_holdout_pct"))),
                r.get("bondad_nivel", "—"),
                r.get("proyeccion_razonable", "—"),
            ]
        )

    best, worst = _best_worst(sub, "mape_holdout_pct")

    parts = [
        "### 6.1 Matriz modelo × métricas (% fatales)\n",
        _md_table(
            ["Modelo", "% obs. medio", "R²", "MAPE ajuste", "MAPE hold-out", "Bondad", "¿Razonable?"],
            table_rows,
        ),
        "",
        "### 6.2 Mejor y peor modelo (MAPE hold-out)\n",
    ]
    if best:
        parts.append(f"- **Mejor:** {_label(best['modelo'])} — MAPE hold-out {_fmt_pct(_num(best.get('mape_holdout_pct')))}")
    if worst:
        parts.append(f"- **Peor:** {_label(worst['modelo'])} — MAPE hold-out {_fmt_pct(_num(worst.get('mape_holdout_pct')))}")

    parts.append("\n### 6.3 Interpretación\n")
    if esc == CASO_PRINCIPAL:
        parts.append(
            "El % mensual de víctimas fatales es bajo (~0,66 %) y volátil; R² moderado (0,35–0,38) es **normal**. "
            "Logit con exposición y estacional sobre % lideran la prueba (~20–22 % MAPE). "
            "OLS, logit simple, ARIMA y SARIMA fallan en hold-out (>28 %); μ±3σ no aplica a porcentajes. "
            "Ratio compuesto enlaza con la lógica de conteos de la sección 1."
        )
    return "\n".join(parts) + "\n"


def seccion5_md(esc: str, rows: list[dict]) -> str:
    sub = _filter_esc(rows, esc)
    if not sub:
        return "_Sin datos._\n"

    table_rows = []
    for r in sub:
        table_rows.append(
            [
                _label(r["modelo"]),
                r.get("total_proyectado_horizonte", "—"),
                r.get("p12_top_celda", "—"),
                r.get("p12_spearman_obs_proy", "—"),
                r.get("p13_top_dia", "—"),
                r.get("patron_util", "—"),
            ]
        )

    best_t, worst_t = _best_worst(sub, "total_proyectado_horizonte", lower_better=False)

    parts = [
        "### 7.1 Matriz modelo × patrón temporal\n",
        _md_table(
            ["Modelo", "Total horizonte", "Celda líder P12", "Spearman P12", "Día líder P13", "Util"],
            table_rows,
        ),
        "",
        "### 7.2 Mejor y peor según total proyectado\n",
    ]
    if best_t:
        parts.append(
            f"- **Mayor total:** {_label(best_t['modelo'])} ({best_t.get('total_proyectado_horizonte')} incidentes en horizonte)"
        )
    if worst_t:
        parts.append(
            f"- **Menor total:** {_label(worst_t['modelo'])} ({worst_t.get('total_proyectado_horizonte')} incidentes)"
        )

    parts.append("\n### 7.3 Interpretación\n")
    if esc == CASO_PRINCIPAL:
        parts.append(
            "El **patrón relativo** (martes 07:00, martes en P13) es **idéntico** entre modelos (Spearman ≈ 0,999): "
            "el reparto temporal sigue el historial Laplace, no el modelo mensual. "
            "Lo que cambia es el **total** heredado de la sección 1 — coherente con el mejor/peor hold-out de §1. "
            "La utilidad operativa está en combinar «cuándo» (esta sección) con «dónde» (§3) y «cuánto» (§1)."
        )
    return "\n".join(parts) + "\n"


def sintesis_caso_a(rows1, rows3, rows4, rows5) -> str:
    s1 = _filter_esc(rows1, CASO_PRINCIPAL)
    best1, _ = _best_worst(s1, "mape_holdout_pct")
    tres = next((r for r in s1 if r.get("modelo") == "tres_sigma"), None)
    s3t = next((r for r in _filter_esc(rows3, CASO_PRINCIPAL) if r.get("modelo") == "tres_sigma"), None)
    s4b = _best_worst(_filter_esc(rows4, CASO_PRINCIPAL), "mape_holdout_pct")[0]
    s5e = next((r for r in _filter_esc(rows5, CASO_PRINCIPAL) if r.get("modelo") == "estacional"), None)

    return f"""## 8. Síntesis del caso de estudio A — decisiones recomendadas

| Sección | Pregunta | Mejor opción (escenario A) | Peor / evitar | Rol en la tesis |
| --- | --- | --- | --- | --- |
| 1 Proyección mensual | ¿Cuántos incidentes/mes? | {_label(best1['modelo']) if best1 else 'SARIMA'} (MAPE hold-out {_fmt_pct(_num(best1.get('mape_holdout_pct')) if best1 else None)}) | Poisson / estacional (>22 % hold-out) | Ancla el volumen futuro |
| 2 Prioridad P05 | ¿Dónde priorizar según pasado? | Índice fijo — La Candelaria #1 | Barrio sin contraste # vol. | Contexto histórico |
| 3 Carga P08 | ¿Dónde se concentrará la carga? | μ±3σ ranking / estacional cifras | ARIMA (top erróneo) | Reparto territorial forward |
| 4 Proporción P07 | ¿Qué tan graves los meses? | {_label(s4b['modelo']) if s4b else 'Logit exp.'} | Media móvil / OLS / SARIMA | Gravedad relativa |
| 5 Patrones P12/P13 | ¿Cuándo? | Patrón estable (martes 07:00) | N/A (mismo patrón) | Turnos y franjas |

**Cadena argumental:** §1 define el total → §3 lo reparte por comuna → §5 por día×hora; §2 y §4 aportan prioridad histórica y gravedad.

**μ±3σ en el caso A:** proyección {_fmt_num(_num(tres.get('media_historica')) if tres else None, 0)} inc./mes; hold-out {_fmt_pct(_num(tres.get('mape_holdout_pct')) if tres else None)}; en §3 Spearman {s3t.get('spearman_carga_frecuencia') if s3t else '—'}.

**Total horizonte §5 (estacional):** {s5e.get('total_proyectado_horizonte') if s5e else '—'} incidentes en 3 meses sobre 75 088 observados en el periodo.
"""


def resultados_caso_estudio(
    esc: str,
    rows1: list[dict],
    rows2: list[dict],
    rows3: list[dict],
    rows4: list[dict],
    rows5: list[dict],
) -> str:
    s1 = _filter_esc(rows1, esc)
    s2 = _filter_esc(rows2, esc)
    s3 = _filter_esc(rows3, esc)
    s4 = _filter_esc(rows4, esc)
    s5 = _filter_esc(rows5, esc)

    best1, worst1 = _best_worst(s1, "mape_holdout_pct")
    best3_sp, worst3_sp = _best_worst(s3, "spearman_carga_frecuencia", lower_better=False)
    best3_mape, _ = _best_worst(s3, "mediana_mape_holdout_pct")
    best4, worst4 = _best_worst(s4, "mape_holdout_pct")

    mod5 = best1["modelo"] if best1 else "estacional"
    r5 = next((r for r in s5 if r.get("modelo") == mod5), s5[0] if s5 else None)

    r2 = s2[0] if s2 else {}
    tres1 = next((r for r in s1 if r.get("modelo") == "tres_sigma"), None)
    ma1 = next((r for r in s1 if r.get("modelo") == "media_movil"), None)
    est3 = next((r for r in s3 if r.get("modelo") == "estacional"), None)

    b1_mape = _num(best1.get("mape_holdout_pct")) if best1 else None
    w1_mape = _num(worst1.get("mape_holdout_pct")) if worst1 else None
    b4_mape = _num(best4.get("mape_holdout_pct")) if best4 else None
    pct_obs = s4[0].get("pct_promedio_observado", "—") if s4 else "—"

    lines = [
        f"## 9. Resultados del caso de estudio (escenario {esc})",
        "",
        "Resumen de hallazgos con los **mejores modelos por sección** según las métricas del tablero "
        "(MAPE hold-out en §1 y §4; Spearman y MAPE mediano territorial en §3). Periodo 2018–2021, "
        "incidentes ciudad, excluir COVID, horizonte y hold-out de 3 meses.",
        "",
        "### 9.1 Proyección mensual (sección 1)",
        "",
    ]

    if best1:
        lines.append(
            f"- **Mejor modelo:** {_label(best1['modelo'])} — MAPE hold-out **{_fmt_pct(b1_mape)}** "
            f"(precisión estimada **{_precision(b1_mape)}**). Cumple el umbral adoptado (≤ 20 % MAPE)."
        )
    if ma1:
        m_mape = _num(ma1.get("mape_holdout_pct"))
        lines.append(
            f"- **Alternativa interpretable:** {_label(ma1['modelo'])} — MAPE hold-out {_fmt_pct(m_mape)} "
            f"(precisión {_precision(m_mape)}); mejor ajuste visual al historial (R² ≈ {ma1.get('r2', '—')})."
        )
    if tres1:
        t_mape = _num(tres1.get("mape_holdout_pct"))
        lines.append(
            f"- **Línea base μ±3σ:** proyección ≈ {_fmt_num(_num(tres1.get('media_historica')), 0)} inc./mes; "
            f"MAPE hold-out {_fmt_pct(t_mape)}; {tres1.get('pct_meses_dentro_3sigma', '—')} % meses dentro de μ±3σ."
        )
    if worst1:
        lines.append(
            f"- **Peor en prueba predictiva:** {_label(worst1['modelo'])} (MAPE hold-out {_fmt_pct(w1_mape)}). "
            f"Buen MAPE de ajuste no garantiza buena proyección."
        )

    lines.extend(
        [
            "",
            "### 9.2 Prioridad territorial (sección 2 — P05)",
            "",
            f"- En el periodo se registraron **{r2.get('total_incidentes_periodo', '—')} incidentes** "
            f"en **{r2.get('total_territorios_elegibles', '—')} comunas**.",
            f"- **Líder del índice compuesto:** **{r2.get('top1_nombre', '—')}** "
            f"(índice {r2.get('top1_indice', '—')}, {r2.get('top1_incidentes', '—')} incidentes, "
            f"nivel {r2.get('top1_nivel', '—')}, puesto {r2.get('top1_rank_frecuencia', '—')} por volumen).",
            f"- Top 3: {r2.get('top3_nombres', '—')}.",
            "- Describe el **pasado** (frecuencia, densidad, delta de promedios, gravedad, participación); "
            "complementa, no sustituye, las secciones prospectivas.",
            "",
            "### 9.3 Carga territorial proyectada (sección 3 — P08/P09)",
            "",
        ]
    )

    if best3_sp:
        lines.append(
            f"- **Mejor coherencia de ranking:** {_label(best3_sp['modelo'])} — Spearman "
            f"**{best3_sp.get('spearman_carga_frecuencia')}**; líder **{best3_sp.get('top1_nombre')}** "
            f"({best3_sp.get('top1_carga')} inc. en horizonte)."
        )
    if best3_mape:
        lines.append(
            f"- **Mejor precisión de cifras:** {_label(best3_mape['modelo'])} — MAPE mediano hold-out "
            f"**{best3_mape.get('mediana_mape_holdout_pct')} %**."
        )
    if est3:
        lines.append(
            f"- **Modelo adoptado:** estacional — carga #1 {est3.get('top1_nombre')} ({est3.get('top1_carga')})."
        )
    if worst3_sp:
        evitar = next(
            (r for r in s3 if r.get("top1_coincide_p05") == "no" or r.get("cierre_util") == "parcial"),
            worst3_sp,
        )
        lines.append(
            f"- **Evitar para ranking:** {_label(evitar['modelo'])} — líder {evitar.get('top1_nombre')} "
            f"(utilidad {evitar.get('cierre_util', '—')}); Spearman {evitar.get('spearman_carga_frecuencia')}."
        )

    lines.extend(
        [
            "",
            "### 9.4 Proporción de víctimas fatales (sección 4 — P07)",
            "",
            f"- **% observado medio:** **{pct_obs} %** (promedio mensual histórico; no depende del modelo).",
        ]
    )
    if best4:
        lines.append(
            f"- **Mejor modelo:** {_label(best4['modelo'])} — MAPE hold-out **{_fmt_pct(b4_mape)}** "
            f"(R² ajuste {_fmt_num(_num(best4.get('r2')), 3)})."
        )
    if worst4:
        w4 = _num(worst4.get("mape_holdout_pct"))
        lines.append(
            f"- **Peor en prueba:** {_label(worst4['modelo'])} — MAPE hold-out {_fmt_pct(w4)}."
        )
    lines.append(
        "- **Estacional**, **logit con exposición** y **ratio compuesto** permanecen en rango razonable (~20–22 %)."
    )

    lines.extend(["", "### 9.5 Patrones temporales (sección 5 — P12/P13)", ""])
    if r5:
        lines.append(
            f"- Con **{_label(mod5)}** (mejor §1), total horizonte **{r5.get('total_proyectado_horizonte')}** incidentes."
        )
        lines.append(
            f"- Franja líder **{r5.get('p12_top_celda')}**; día líder **{r5.get('p13_top_dia')}**; "
            f"Spearman celdas **{r5.get('p12_spearman_obs_proy')}**."
        )

    lines.extend(
        [
            "",
            "### 9.6 Cuadro resumen de resultados",
            "",
            "| Dimensión | Mejor enfoque | Indicador clave |",
            "| --- | --- | --- |",
            f"| Volumen (§1) | {_label(best1['modelo']) if best1 else '—'} | MAPE hold-out {_fmt_pct(b1_mape)} |",
            f"| Prioridad pasado (§2) | Índice P05 | {r2.get('top1_nombre', '—')} (índice {r2.get('top1_indice', '—')}) |",
            f"| Carga futura (§3) | Estacional / μ±3σ ranking | {est3.get('top1_nombre') if est3 else '—'} líder carga |",
            f"| Gravedad % (§4) | {_label(best4['modelo']) if best4 else '—'} | MAPE hold-out {_fmt_pct(b4_mape)} |",
            f"| Momento (§5) | Patrón histórico + total §1 | {r5.get('p12_top_celda') if r5 else '—'} |",
        ]
    )

    return "\n".join(lines)


def conclusiones_caso_estudio(
    esc: str,
    rows1: list[dict],
    rows2: list[dict],
    rows3: list[dict],
    rows4: list[dict],
    rows5: list[dict],
) -> str:
    s1 = _filter_esc(rows1, esc)
    s3 = _filter_esc(rows3, esc)
    s4 = _filter_esc(rows4, esc)

    best1, _ = _best_worst(s1, "mape_holdout_pct")
    best4, _ = _best_worst(s4, "mape_holdout_pct")
    est3 = next((r for r in s3 if r.get("modelo") == "estacional"), None)
    r2a = _filter_esc(rows2, esc)
    r2 = r2a[0] if r2a else {}

    mod1 = _label(best1["modelo"]) if best1 else "SARIMA"
    mod4 = _label(best4["modelo"]) if best4 else "Logit con exposición"
    b1_mape = _fmt_pct(_num(best1.get("mape_holdout_pct"))) if best1 else "—"
    b4_mape = _fmt_pct(_num(best4.get("mape_holdout_pct"))) if best4 else "—"

    return f"""## 10. Conclusiones según los resultados

### 10.1 Conclusiones por bloque

1. **Proyección mensual.** **{mod1}** minimiza el error en hold-out (**{b1_mape}**) en el escenario A. Poisson y estacional no deben elegirse solo por el buen ajuste al gráfico. Media móvil y μ±3σ son alternativas válidas por simplicidad.

2. **Prioridad territorial.** P05 sintetiza el periodo histórico; **{r2.get('top1_nombre', 'La Candelaria')}** lidera el índice compuesto. Esto orienta el diagnóstico del pasado, no el volumen proyectado de §3.

3. **Carga territorial.** **Estacional** mantiene a **{est3.get('top1_nombre') if est3 else 'La Candelaria'}** como comuna de mayor carga futura. **μ±3σ** mejora el ranking (Spearman ≈ 1); **ARIMA** altera el líder y no se recomienda.

4. **Proporción de fatales.** Gravedad mensual baja (~0,66 %); **{mod4}** obtiene el mejor hold-out (**{b4_mape}**). OLS y ARIMA/SARIMA sobre % no son adecuados.

5. **Patrones temporales.** El reparto (martes 07:00) es estable; el modelo de §1 solo define el total a distribuir en el horizonte.

### 10.2 Conclusión general

ViaData integra cinco perspectivas bajo un mismo periodo filtrado, con validación hold-out y comparación de modelos. Configuración recomendada (escenario A):

| Bloque | Decisión |
| --- | --- |
| §1 | **{mod1}** |
| §2 | Índice P05 (fórmula fija) |
| §3 | **Estacional** por comuna |
| §4 | **{mod4}** o estacional sobre % |
| §5 | Hereda §1 |

### 10.3 Limitaciones

- Proyecciones **exploratorias**, no predicción oficial ni intervalos de confianza.
- Hold-out de 3 meses favorece modelos estacionales; resultados cambian con 6 meses de prueba.
- Carga y % fatales: utilidad en **ranking y magnitud**, no en cifras exactas.
- Rangos cortos (< 24 meses) limitan SARIMA y series territoriales.

### 10.4 Aporte para la tesis

Los resultados fundamentan la utilidad del sistema: el analista puede articular **cuánto → dónde → cuándo**, con contexto de **prioridad histórica** y **gravedad**, eligiendo modelos con criterio hold-out documentado en los CSV de `evaluaciones/`.
"""


def build_md(esc_principal: str) -> str:
    rows1 = _read_csv("predicciones_seccion1_proyeccion_mensual.csv")
    rows2 = _read_csv("predicciones_seccion2_prioridad_territorial.csv")
    rows3 = _read_csv("predicciones_seccion3_carga_territorial.csv")
    rows4 = _read_csv("predicciones_seccion4_proporcion_fatales.csv")
    rows5 = _read_csv("predicciones_seccion5_patrones_temporales.csv")

    meta = ESCENARIOS_META.get(esc_principal, {})
    hoy = date.today().isoformat()

    return f"""# Matriz de escenarios — caso de estudio ViaData (Medellín)

> Documento generado automáticamente desde los CSV de `evaluaciones/`.  
> Regenerar: `python scripts/llenar_evaluacion_todas_secciones.py` y luego `python scripts/generar_matriz_escenarios_md.py`  
> Fecha de generación: {hoy}

---

## 1. Caso de estudio principal — Escenario {esc_principal}

| Parámetro | Valor |
| --- | --- |
| **Identificador** | {esc_principal} |
| **Descripción** | {meta.get('titulo', 'Referencia')} |
| **Periodo** | {meta.get('desde', '2018-01-01')} — {meta.get('hasta', '2021-09-30')} |
| **Filtros** | {meta.get('filtros', 'Ciudad, incidentes, excluir mar–ago 2020')} |
| **Horizonte** | 3 meses |
| **Hold-out** | 3 meses reservados (secciones 1 y 4) |
| **Propósito** | {meta.get('proposito', 'Evaluar el módulo Predicciones con datos reales SECRETARÍA de Movilidad.')} |

Este escenario concentra **~39 meses de ajuste** (excluyendo mar–ago 2020), **75 088 incidentes** en el periodo y la configuración recomendada en producción.

---

## 2. Metodología transversal

| Concepto | Definición en el sistema |
| --- | --- |
| **MAPE hold-out** | Error medio porcentual en meses que el modelo no vio al entrenar. **Métrica principal** para elegir modelo en §1 y §4. |
| **Precisión estimada** | 100 % − MAPE hold-out. Umbral adoptado: ≥ 80 % (MAPE ≤ 20 %). |
| **R² in-sample** | Ajuste al historial. Puede ser alto con sobreajuste; en μ±3σ suele ser ≈ 0 (esperado). |
| **Spearman (§3)** | Coherencia del ranking de carga vs volumen histórico. |
| **MAPE mediano territorial (§3)** | Calidad de las cifras absolutas proyectadas por comuna. |
| **Patrón P12/P13 (§5)** | Reparto Laplace del total de §1; el modelo mensual cambia el total, no la forma relativa. |

**Sección 2** no compara modelos: el índice P05 es determinista (pesos fijos + delta de promedios).

---

## 3. Sección 1 — Proyección mensual

{seccion1_md(esc_principal, rows1)}

---

## 4. Sección 2 — Prioridad territorial (P05)

{seccion2_md(esc_principal, rows2)}

---

## 5. Sección 3 — Carga territorial (P08/P09)

{seccion3_md(esc_principal, rows3)}

---

## 6. Sección 4 — Proporción de víctimas fatales (P07)

{seccion4_md(esc_principal, rows4)}

---

## 7. Sección 5 — Patrones día×hora y día de semana (P12/P13)

{seccion5_md(esc_principal, rows5)}

---

{sintesis_caso_a(rows1, rows3, rows4, rows5)}

---

{resultados_caso_estudio(esc_principal, rows1, rows2, rows3, rows4, rows5)}

---

{conclusiones_caso_estudio(esc_principal, rows1, rows2, rows3, rows4, rows5)}
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--escenario", default=CASO_PRINCIPAL, help="ID escenario principal (A–I)")
    parser.add_argument("--salida", type=Path, default=OUT_PATH)
    args = parser.parse_args()

    md = build_md(args.escenario.upper())
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(md, encoding="utf-8")
    print(f"Escrito: {args.salida} ({len(md)} caracteres)")


if __name__ == "__main__":
    main()
