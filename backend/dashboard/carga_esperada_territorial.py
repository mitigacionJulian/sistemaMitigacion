"""
P08 — Categoría de carga esperada (alto / medio / bajo) por comuna o barrio.

Usa proyección de incidentes (modelo estacional por defecto) sumada en el horizonte
y clasifica por terciles entre territorios elegibles.
"""
from __future__ import annotations

from datetime import date
from statistics import median
from typing import Any, Literal

from .kpis import FiltrosKpi
from .predicciones_mensuales import (
    HOLDOUT_MESES_DEFAULT,
    MA_VENTANA_DEFAULT,
    ArimaOpciones,
    _build_single,
    normalize_modelo_proyeccion,
)
from .prioridad_territorial import MIN_INCIDENTES_TERRITORIO, _query_totales_territorio
from .territorio_sql import meta_filtros_dict, nota_modo_territorio

NivelTerritorio = Literal["comuna", "barrio"]
# Territorios con menos incidentes en el periodo distorsionan el MAPE agregado.
MIN_INCIDENTES_NUCLEO_BONDAD = 1000


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
    arima_opciones: ArimaOpciones | None = None,
    holdout_meses: int = HOLDOUT_MESES_DEFAULT,
) -> dict[str, Any] | None:
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
        holdout_meses=holdout_meses,
        arima_opciones=arima_opciones,
    )
    if bloque["meta"].get("sin_modelo"):
        return None
    carga = sum(float(r.get("proyectados") or 0) for r in bloque["proyeccion"])
    coef = bloque["meta"].get("coeficientes") or {}
    hold = bloque["meta"].get("holdout") or {}
    holdout_activo = bool(hold.get("activo"))
    mape_hold = hold.get("mape_pct") if holdout_activo else None
    return {
        "carga": round(carga, 2),
        "r2": coef.get("r2"),
        "mape_pct": coef.get("mape_pct"),
        "mape_holdout_pct": float(mape_hold) if mape_hold is not None else None,
        "holdout_activo": holdout_activo,
    }


def _tid_row(row: dict[str, Any], nivel: NivelTerritorio) -> int:
    return int(row["comuna_id"] if nivel == "comuna" else row["barrio_id"])


def _spearman(rank_a: dict[int, int], rank_b: dict[int, int]) -> float | None:
    common = [k for k in rank_a if k in rank_b]
    n = len(common)
    if n < 3:
        return None
    d2 = sum((rank_a[k] - rank_b[k]) ** 2 for k in common)
    return 1.0 - (6.0 * d2) / (n * (n * n - 1))


def _coherencia_carga_frecuencia(filas: list[dict[str, Any]], nivel: NivelTerritorio) -> dict[str, Any]:
    if len(filas) < 3:
        return {"spearman": None, "overlap_top5": None, "top1_rank_frecuencia": None}
    by_freq = sorted(filas, key=lambda r: r["incidentes_periodo"], reverse=True)
    freq_rank = {_tid_row(r, nivel): i + 1 for i, r in enumerate(by_freq)}
    carga_rank = {_tid_row(r, nivel): i + 1 for i, r in enumerate(filas)}
    top5_carga = {_tid_row(r, nivel) for r in filas[:5]}
    top5_freq = {_tid_row(r, nivel) for r in by_freq[:5]}
    top1_tid = _tid_row(filas[0], nivel)
    return {
        "spearman": round(_spearman(carga_rank, freq_rank), 4)
        if _spearman(carga_rank, freq_rank) is not None
        else None,
        "overlap_top5": len(top5_carga & top5_freq),
        "top1_rank_frecuencia": freq_rank.get(top1_tid),
    }


def _nivel_confianza_ranking(
    spearman: float | None,
    top1_rank_frec: int | None,
    overlap_top5: int | None,
) -> str:
    sp = spearman if spearman is not None else 0.0
    overlap = overlap_top5 or 0
    top1_rf = top1_rank_frec or 99
    if sp >= 0.75 and top1_rf <= 3 and overlap >= 3:
        return "bueno"
    if sp >= 0.5 or top1_rf <= 5 or overlap >= 2:
        return "moderado"
    return "bajo"


def _nivel_confianza_cifras(
    mediana_mape_holdout: float | None,
    mape_ponderado: float | None,
    mediana_nucleo: float | None,
    pct_holdout_aceptable: float | None,
) -> str:
    if mediana_mape_holdout is None:
        return "bajo"
    aceptable = pct_holdout_aceptable or 0.0
    pond = mape_ponderado if mape_ponderado is not None else mediana_mape_holdout
    nuc = mediana_nucleo if mediana_nucleo is not None else mediana_mape_holdout
    if mediana_mape_holdout <= 20 and aceptable >= 60:
        return "bueno"
    if pond <= 30 or nuc <= 25 or aceptable >= 35:
        return "moderado"
    return "bajo"


def _nivel_confianza_modelo(
    nivel_ranking: str,
    nivel_cifras: str,
) -> str:
    """Nivel global: prioriza ranking (uso P08/P09) si las cifras no alcanzan umbral ciudad."""
    orden = {"bueno": 2, "moderado": 1, "bajo": 0}
    if orden[nivel_ranking] >= orden[nivel_cifras]:
        return nivel_ranking
    return nivel_cifras


def _mape_ponderado_y_nucleo(
    metricas: list[dict[str, Any]],
    filas: list[dict[str, Any]],
) -> tuple[float | None, float | None, int]:
    pairs: list[tuple[float, int]] = []
    nucleo_mapes: list[float] = []
    for m, row in zip(metricas, filas, strict=True):
        mape = m.get("mape_holdout_pct")
        if not m.get("holdout_activo") or mape is None:
            continue
        inc = int(row["incidentes_periodo"])
        pairs.append((float(mape), inc))
        if inc >= MIN_INCIDENTES_NUCLEO_BONDAD:
            nucleo_mapes.append(float(mape))
    if not pairs:
        return None, None, 0
    total_inc = sum(w for _, w in pairs)
    pond = round(sum(m * w for m, w in pairs) / total_inc, 2) if total_inc else None
    med_nuc = round(median(nucleo_mapes), 2) if nucleo_mapes else None
    return pond, med_nuc, len(nucleo_mapes)


def _recomendaciones_mejora(
    *,
    nivel_ranking: str,
    nivel_cifras: str,
    modelo: str,
    nivel: NivelTerritorio,
    pct_aceptable: float | None,
    mediana_mape: float | None,
) -> list[str]:
    recs: list[str] = []
    if nivel == "barrio":
        recs.append(
            "Prefiera nivel comuna: muchos barrios tienen pocos incidentes mensuales y el error de "
            "proyección se dispara."
        )
    if modelo in ("arima", "sarima"):
        recs.append(
            "ARIMA/SARIMA por territorio suelen ser inestables; use estacional o media móvil para el ranking."
        )
    if nivel_cifras == "bajo":
        recs.append(
            "El MAPE territorial casi nunca iguala al de la sección 1 (serie ciudad): cada comuna tiene "
            "menos datos mensuales. Use esta sección para **ordenar** territorios, no para cifras exactas."
        )
        recs.append(
            "Complemente con la sección 2 (P05) para priorización integral y con la sección 1 para el "
            "volumen total de la ciudad."
        )
    if pct_aceptable is not None and pct_aceptable < 40:
        recs.append(
            f"Solo ~{pct_aceptable:g} % de territorios pasan el umbral del 20 % MAPE; comunas pequeñas "
            f"(<{MIN_INCIDENTES_NUCLEO_BONDAD} incidentes en el periodo) distorsionan la mediana."
        )
    if nivel_ranking in ("bueno", "moderado") and nivel_cifras == "bajo":
        recs.append(
            "Si el ranking es coherente (Spearman alto), P08/P09 siguen siendo útiles para comparar "
            "territorios entre sí aunque el MAPE absoluto sea alto."
        )
    if mediana_mape is not None and mediana_mape > 30:
        recs.append(
            "Amplíe el rango de fechas (≥ 3 años), mantenga «Excluir mar–ago 2020» y evite filtros muy estrechos."
        )
    if not recs:
        recs.append("Mantenga estacional, horizonte 3 meses y valide el top 3 frente a la columna # vol.")
    return recs


def _agregar_bondad_territorial(
    metricas: list[dict[str, Any]],
    filas: list[dict[str, Any]],
    coherencia: dict[str, Any],
    *,
    territorios_totales: int,
    modelo: str,
    holdout_meses: int,
    nivel: NivelTerritorio,
) -> dict[str, Any]:
    holdout_mapes = [
        float(m["mape_holdout_pct"])
        for m in metricas
        if m.get("holdout_activo") and m.get("mape_holdout_pct") is not None
    ]
    r2_vals = [float(m["r2"]) for m in metricas if m.get("r2") is not None]
    proyectables = len(metricas)
    mediana_hold = round(median(holdout_mapes), 2) if holdout_mapes else None
    mediana_r2 = round(median(r2_vals), 4) if r2_vals else None
    pct_aceptable = (
        round(100.0 * sum(1 for x in holdout_mapes if x <= 20) / len(holdout_mapes), 1)
        if holdout_mapes
        else None
    )
    precision_mediana = (
        round(max(0.0, min(100.0, 100.0 - mediana_hold)), 1) if mediana_hold is not None else None
    )
    spearman = coherencia.get("spearman")
    mape_pond, mediana_nucleo, n_nucleo = _mape_ponderado_y_nucleo(metricas, filas)
    nivel_ranking = _nivel_confianza_ranking(
        spearman,
        coherencia.get("top1_rank_frecuencia"),
        coherencia.get("overlap_top5"),
    )
    nivel_cifras = _nivel_confianza_cifras(mediana_hold, mape_pond, mediana_nucleo, pct_aceptable)
    nivel = _nivel_confianza_modelo(nivel_ranking, nivel_cifras)
    recomendaciones = _recomendaciones_mejora(
        nivel_ranking=nivel_ranking,
        nivel_cifras=nivel_cifras,
        modelo=modelo,
        nivel=nivel,
        pct_aceptable=pct_aceptable,
        mediana_mape=mediana_hold,
    )

    interpretacion = _interpretacion_bondad_agregada(
        nivel_ranking,
        nivel_cifras,
        mediana_hold,
        mape_pond,
        mediana_nucleo,
        n_nucleo,
        precision_mediana,
        pct_aceptable,
        proyectables,
        territorios_totales,
        spearman,
        coherencia.get("top1_rank_frecuencia"),
    )

    return {
        "holdout_meses": holdout_meses,
        "territorios_totales_periodo": territorios_totales,
        "territorios_proyectables": proyectables,
        "territorios_con_holdout": len(holdout_mapes),
        "territorios_nucleo_bondad": n_nucleo,
        "min_incidentes_nucleo": MIN_INCIDENTES_NUCLEO_BONDAD,
        "mediana_mape_holdout_pct": mediana_hold,
        "mape_ponderado_incidentes_pct": mape_pond,
        "mediana_mape_nucleo_pct": mediana_nucleo,
        "mediana_r2_ajuste": mediana_r2,
        "pct_territorios_holdout_aceptable": pct_aceptable,
        "precision_estimada_mediana_pct": precision_mediana,
        "umbral_mape_aceptable_pct": 20,
        "spearman_carga_frecuencia": spearman,
        "overlap_top5_carga_frecuencia": coherencia.get("overlap_top5"),
        "top1_rank_frecuencia": coherencia.get("top1_rank_frecuencia"),
        "nivel_confianza": nivel,
        "nivel_confianza_ranking": nivel_ranking,
        "nivel_confianza_cifras": nivel_cifras,
        "interpretacion": interpretacion,
        "recomendaciones_mejora": recomendaciones,
        "guia_eleccion_modelo": _guia_eleccion_modelo(modelo, holdout_meses),
        "nota_limitacion_territorial": (
            "La sección 1 proyecta la ciudad agregada (más datos = mejor MAPE). Aquí cada territorio "
            "se ajusta aparte: el ranking relativo suele ser más fiable que el número exacto de incidentes."
        ),
    }


def _interpretacion_bondad_agregada(
    nivel_ranking: str,
    nivel_cifras: str,
    mediana_mape: float | None,
    mape_ponderado: float | None,
    mediana_nucleo: float | None,
    n_nucleo: int,
    precision_mediana: float | None,
    pct_aceptable: float | None,
    proyectables: int,
    totales: int,
    spearman: float | None,
    top1_rank_frec: int | None,
) -> str:
    partes: list[str] = [
        f"Se ajustó el modelo en {proyectables} de {totales} territorios con datos suficientes."
    ]
    if spearman is not None:
        partes.append(f"Coherencia del ranking con volumen histórico (Spearman): {spearman:g}.")
    if nivel_ranking == "bueno":
        partes.append(
            "El orden entre territorios es confiable para priorizar (uso P08/P09 comparativo)."
        )
    elif nivel_ranking == "moderado":
        partes.append("El ranking es aceptable; revise el top 3 y la columna # vol.")
    else:
        partes.append("El ranking es poco confiable; pruebe otro modelo o nivel comuna.")

    if mediana_mape is not None and precision_mediana is not None:
        partes.append(
            f"MAPE mediano en prueba: {mediana_mape:g} % (precisión ≈ {precision_mediana:g} %)."
        )
    if mape_ponderado is not None:
        partes.append(f"MAPE ponderado por incidentes del periodo: {mape_ponderado:g} %.")
    if mediana_nucleo is not None and n_nucleo:
        partes.append(
            f"En el núcleo de {n_nucleo} territorios con ≥ {MIN_INCIDENTES_NUCLEO_BONDAD} incidentes, "
            f"MAPE mediano {mediana_nucleo:g} %."
        )
    if pct_aceptable is not None:
        partes.append(f"{pct_aceptable:g} % de territorios con prueba ≤ 20 % MAPE (criterio sección 1).")

    if nivel_cifras == "bajo":
        partes.append(
            "Las cifras absolutas de incidentes proyectados son inciertas; no las use como presupuesto exacto."
        )
    elif nivel_cifras == "moderado":
        partes.append("Las cifras son orientativas; priorice el orden relativo entre territorios.")
    else:
        partes.append("Las cifras proyectadas son razonables en conjunto para planificación exploratoria.")

    if top1_rank_frec is not None and top1_rank_frec > 5:
        partes.append(
            f"El #1 por carga es puesto #{top1_rank_frec} por volumen; compare con estacional u OLS."
        )
    return " ".join(partes)


def _guia_eleccion_modelo(modelo: str, holdout_meses: int) -> str:
    return (
        "Evalúe dos cosas por separado: (A) **ranking** — Spearman y # vol.; "
        "(B) **cifras** — MAPE mediano y ponderado. "
        "En Medellín el ranking territorial suele ser bueno aunque el MAPE supere 20 %, porque cada comuna "
        "tiene menos historia que la ciudad entera. "
        f"Cambie el modelo y compare: estacional, μ±3σ u OLS para comunas; "
        f"μ±3σ sirve como línea base (media constante) con bandas de control; "
        f"evite ARIMA/SARIMA salvo análisis puntual. "
        f"La prueba usa {holdout_meses} meses reservados por territorio."
    )


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
    arima_opciones: ArimaOpciones | None = None,
) -> dict[str, Any]:
    filtros = filtros or FiltrosKpi()
    niv: NivelTerritorio = "barrio" if nivel == "barrio" else "comuna"
    hm = max(1, min(12, int(horizonte_meses)))
    limite = min(max(int(limite), 1), 50)
    mod = normalize_modelo_proyeccion(modelo)

    totales = _query_totales_territorio(inicio, fin, filtros, niv)
    filas: list[dict[str, Any]] = []
    metricas: list[dict[str, Any]] = []

    for tid, t in totales.items():
        fit = _carga_proyectada_territorio(
            inicio, fin, filtros, niv, tid, hm, mod, excluir_covid, ventana_ma, arima_opciones
        )
        if fit is None:
            continue
        metricas.append(fit)
        row: dict[str, Any] = {
            "carga_proyectada_horizonte": fit["carga"],
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
    coherencia = _coherencia_carga_frecuencia(filas, niv)
    by_freq = sorted(filas, key=lambda r: r["incidentes_periodo"], reverse=True)
    freq_rank_map = {_tid_row(r, niv): i + 1 for i, r in enumerate(by_freq)}

    ranking: list[dict[str, Any]] = []
    for i, row in enumerate(filas[:limite], start=1):
        row = {**row}
        row["rank"] = i
        row["rank_frecuencia"] = freq_rank_map.get(_tid_row(row, niv), i)
        row["categoria_esperada"] = _nivel_tercil(row["carga_proyectada_horizonte"], p33, p66)
        ranking.append(row)

    bondad = _agregar_bondad_territorial(
        metricas,
        filas,
        coherencia,
        territorios_totales=len(totales),
        modelo=mod,
        holdout_meses=HOLDOUT_MESES_DEFAULT,
        nivel=niv,
    )

    alerta_liderazgo = None
    top1_rf = coherencia.get("top1_rank_frecuencia")
    if ranking and top1_rf is not None and top1_rf > 5:
        nombre = (
            ranking[0].get("comuna_nombre")
            if niv == "comuna"
            else ranking[0].get("barrio_nombre")
        )
        alerta_liderazgo = {
            "mensaje": (
                f"#{ranking[0]['rank']} por carga proyectada es {nombre}, pero por volumen del periodo "
                f"ocupa el puesto #{top1_rf}. El modelo puede estar reordenando territorios; "
                "compare con otro modelo o con la sección 2 (P05)."
            ),
        }

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
        "bondad_agregada": bondad,
        **_meta_carga_textos(mod, hm, niv, p33, p66, ventana_ma=ventana_ma),
    }
    if alerta_liderazgo:
        meta_out["alerta_liderazgo"] = alerta_liderazgo
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
            "rank_frecuencia": "Puesto del territorio si ordenara solo por incidentes del periodo.",
        },
        "diferencia_p05": (
            "P05 (prioridad): mezcla frecuencia, tendencia pasada, % fatales y participación. "
            "P08: solo proyección futura de incidentes."
        ),
    }
