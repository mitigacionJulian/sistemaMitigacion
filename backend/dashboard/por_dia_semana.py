"""
Serie por día de semana: periodo actual vs mismo rango del año anterior.

La semaforización describe **concentración relativa de incidentes por día** dentro de la semana
del periodo filtrado (no es probabilidad de accidente ni riesgo individual).
"""
from __future__ import annotations

from datetime import date
from typing import Any

from django.db import connection

from .kpis import FiltrosKpi, _shift_year_back
from .territorio_sql import append_filtros_territoriales, meta_filtros_dict, nota_modo_territorio

_DIA_LABEL = {
    0: "Domingo",
    1: "Lunes",
    2: "Martes",
    3: "Miércoles",
    4: "Jueves",
    5: "Viernes",
    6: "Sábado",
}

# Reparto uniforme: 100% / 7 días ≈ 14,29% por día si la carga fuera la misma todos los días.
_PCT_UNIFORME_DIA = 100.0 / 7.0


def _query_por_dia(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi,
) -> dict[int, tuple[int, int]]:
    where = ["i.fecha_incidente >= %s", "i.fecha_incidente <= %s"]
    params: list[Any] = [inicio, fin]

    append_filtros_territoriales(where, params, filtros)

    wh = " AND ".join(where)
    sql = f"""
    SELECT
      EXTRACT(DOW FROM i.fecha_incidente)::int AS dia_semana,
      COUNT(DISTINCT i.id)::bigint AS total_incidentes,
      COUNT(v.id)::bigint AS total_victimas
    FROM incidente i
    LEFT JOIN victima v ON v.incidente_id = i.id
    WHERE {wh}
    GROUP BY 1
    ORDER BY 1
    """

    out: dict[int, tuple[int, int]] = {}
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        for row in cursor.fetchall():
            d = int(row[0])
            out[d] = (int(row[1] or 0), int(row[2] or 0))
    return out


def _total_incidentes_semana(act: dict[int, tuple[int, int]]) -> int:
    return sum(act.get(d, (0, 0))[0] for d in range(7))


def _carga_nivel_vs_uniforme(ratio: float) -> str:
    """
    ratio = participacion_pct / (100/7).
    1,0 = ese día tiene la misma carga que en un reparto perfectamente uniforme.
    """
    if ratio >= 1.45:
        return "alto"
    if ratio >= 1.12:
        return "medio"
    return "bajo"


def build_dia_semana_payload(
    inicio: date,
    fin: date,
    filtros: FiltrosKpi | None = None,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    inicio_ant = _shift_year_back(inicio)
    fin_ant = _shift_year_back(fin)

    act = _query_por_dia(inicio, fin, filtros)
    ant = _query_por_dia(inicio_ant, fin_ant, filtros)

    total_inc_act = _total_incidentes_semana(act)

    serie: list[dict[str, Any]] = []
    for d in range(7):
        inc_a, vic_a = act.get(d, (0, 0))
        inc_b, vic_b = ant.get(d, (0, 0))
        participacion = (100.0 * inc_a / total_inc_act) if total_inc_act > 0 else 0.0
        ratio = (participacion / _PCT_UNIFORME_DIA) if _PCT_UNIFORME_DIA > 0 else 0.0
        nivel = _carga_nivel_vs_uniforme(ratio)
        serie.append(
            {
                "dia_semana": d,
                "dia": _DIA_LABEL[d],
                "incidentes_periodo_actual": inc_a,
                "victimas_periodo_actual": vic_a,
                "incidentes_periodo_anterior": inc_b,
                "victimas_periodo_anterior": vic_b,
                "participacion_incidentes_pct": round(participacion, 2),
                "ratio_vs_reparto_uniforme": round(ratio, 3),
                "carga_dia_nivel": nivel,
                # Alias legacy (mismo valor; preferir claves nuevas en clientes nuevos).
                "riesgo_score": round(participacion, 2),
                "riesgo_nivel": nivel,
            }
        )

    return {
        "meta": {
            "fecha_inicio": inicio.isoformat(),
            "fecha_fin": fin.isoformat(),
            "fecha_inicio_anterior": inicio_ant.isoformat(),
            "fecha_fin_anterior": fin_ant.isoformat(),
            "criterio_carga_por_dia": {
                "participacion_incidentes_pct": (
                    "Porcentaje de incidentes del periodo actual que ocurrieron en ese día de la semana. "
                    "Los siete valores suman 100%. No es probabilidad de accidente."
                ),
                "ratio_vs_reparto_uniforme": (
                    "participacion_incidentes_pct / (100/7). Valor 1,0 = misma carga que si los incidentes "
                    "se repartieran por igual entre los siete días."
                ),
                "carga_dia_nivel": (
                    "Semáforo por concentración frente al reparto uniforme: alto si ratio ≥ 1,45; "
                    "medio si ratio ≥ 1,12; bajo en caso contrario."
                ),
            },
            "aliases_legacy": (
                "riesgo_score = participacion_incidentes_pct; riesgo_nivel = carga_dia_nivel "
                "(nombres antiguos)."
            ),
            "filtros": meta_filtros_dict(filtros),
            "nota_territorio": nota_modo_territorio(filtros.modo_territorio),
        },
        "serie": serie,
    }
