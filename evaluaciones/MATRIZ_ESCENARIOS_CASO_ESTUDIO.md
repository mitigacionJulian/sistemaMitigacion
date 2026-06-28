# Matriz de escenarios — caso de estudio ViaData (Medellín)

> Documento generado automáticamente desde los CSV de `evaluaciones/`.  
> Regenerar: `python scripts/llenar_evaluacion_todas_secciones.py` y luego `python scripts/generar_matriz_escenarios_md.py`  
> Fecha de generación: 2026-06-27

---

## 1. Caso de estudio principal — Escenario A

| Parámetro | Valor |
| --- | --- |
| **Identificador** | A |
| **Descripción** | Ciudad completa — referencia principal |
| **Periodo** | 2018-01-01 — 2021-09-30 |
| **Filtros** | Incidentes, territorio registro Mede, excluir mar–ago 2020 |
| **Horizonte** | 3 meses |
| **Hold-out** | 3 meses reservados (secciones 1 y 4) |
| **Propósito** | Caso de estudio principal para sustentar el sistema a nivel municipal. |

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

### 3.1 Matriz modelo × métricas

| Modelo | R² ajuste | MAPE ajuste | MAPE hold-out | Precisión est. | ¿Razonable? | Notas |
| --- | --- | --- | --- | --- | --- | --- |
| OLS | 0,007 | 11,21 % | 18,92 % | 81,1 % | parcial | hold-out MAPE 18.92% (~81.1% prec); R2 bajo in-sample |
| Estacional | 0,514 | 8,38 % | 22,44 % | 77,6 % | parcial | hold-out MAPE 22.44% (~77.6% prec) |
| Poisson | 0,524 | 8,30 % | 22,54 % | 77,5 % | parcial | hold-out MAPE 22.54% (~77.5% prec) |
| Media móvil | 0,602 | 6,52 % | 15,71 % | 84,3 % | si | hold-out MAPE 15.71% (~84.3% prec); buen in-sample |
| μ±3σ | 0,000 | 11,25 % | 17,19 % | 82,8 % | si | hold-out MAPE 17.19% (~82.8% prec); μ=1753.359 σ=247.56; 100.0% meses en μ±3σ |
| ARIMA | 0,000 | 10,95 % | 19,90 % | 80,1 % | parcial | hold-out MAPE 19.9% (~80.1% prec); R2 bajo in-sample |
| SARIMA | 0,000 | 13,14 % | 12,62 % | 87,4 % | si | hold-out MAPE 12.62% (~87.4% prec); R2 bajo in-sample |

### 3.2 Mejor y peor modelo (criterio: MAPE hold-out)

- **Mejor:** SARIMA — MAPE hold-out 12,62 % (precisión estimada 87,4 %). Cumple umbral ≤ 20 %.
- **Peor:** Poisson — MAPE hold-out 22,54 % (precisión estimada 77,5 %). Suele sobreajustar el in-sample o ignorar estacionalidad.

### 3.3 Interpretación para el caso de estudio

La prueba con 3 meses reservados desempata modelos que en el ajuste parecen equivalentes. Poisson y estacional muestran buen MAPE in-sample (~8 %) pero superan 22 % en hold-out; no deben elegirse solo por R² o MAPE bajo el gráfico. SARIMA minimiza el error predictivo; media móvil y μ±3σ son alternativas interpretables con precisión ≥ 82 %.

**μ±3σ:** media ≈ 1753 incidentes/mes; banda [1011 – 2496]; 100 % meses dentro. MAPE hold-out 17,19 % — útil como línea base y para sustentar estabilidad del historial, no para captar picos mensuales.


---

## 4. Sección 2 — Prioridad territorial (P05)

### 4.1 Resultado del escenario (sin comparación de modelos)

La sección 2 usa **fórmula fija** (índice compuesto P05); no hay selector de modelo.

| Indicador | Valor |
| --- | --- |
| Nivel | comuna |
| Territorios elegibles | 22 |
| Incidentes en periodo | 75088 |
| #1 índice | **La Candelaria** (índice 62,6) |
| #1 por volumen | Puesto 1 |
| Nivel prioridad #1 | alto |
| Spearman índice↔volumen | 0,8498 |
| Utilidad documentada | si |

### 4.2 Interpretación

El ranking resume **dónde concentró el problema en el pasado** (frecuencia, densidad, delta de promedios, gravedad, participación). 
Complementa la proyección forward de las secciones 1 y 3: un territorio líder en P05 no implica automáticamente el mayor volumen proyectado en P08.
Para barrios (escenario B) la utilidad es **parcial** — conviene contrastar con la vista «solo por frecuencia».


---

## 5. Sección 3 — Carga territorial (P08/P09)

### 5.1 Matriz modelo × ranking y cifras

| Modelo | Top carga | Carga #1 | Spearman | MAPE med. hold-out | Conf. ranking | Conf. cifras | Util |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Estacional | La Candelaria | 982,2 | 0,9492 | 33,16 % | bueno | bajo | si |
| OLS | La Candelaria | 939,56 | 0,9639 | 26,27 % | bueno | moderado | si |
| Media móvil | La Candelaria | 840,99 | 0,8227 | 24,16 % | bueno | moderado | si |
| μ±3σ | La Candelaria | 906,45 | 0,9989 | 21,29 % | bueno | moderado | si |
| ARIMA | Sin Inf | 1088,17 | 0,8001 | 45,52 % | moderado | bajo | parcial |
| SARIMA | La Candelaria | 907,53 | 0,8001 | 58,67 % | bueno | bajo | si |

### 5.2 Mejor y peor modelo

**Ranking (Spearman carga↔volumen):**
- Mejor: **μ±3σ** (ρ = 0,9989)
- Peor: **SARIMA** (ρ = 0,8001)

**Cifras absolutas (MAPE mediano hold-out por territorio):**
- Mejor: **μ±3σ** (21,29 %)
- Peor: **SARIMA** (58,67 %)

### 5.3 Interpretación

Hay **dos criterios** que pueden divergir: μ±3σ logra el ranking más coherente con el volumen histórico y el MAPE territorial más bajo, pero proyecta una carga constante por comuna. Estacional es la opción adoptada para captar variación mensual; ARIMA degradó el ranking (#1 erróneo: Sin Inf). La carga no debe leerse como presupuesto exacto: el MAPE mediano ~21–33 % indica orden de magnitud.


---

## 6. Sección 4 — Proporción de víctimas fatales (P07)

### 6.1 Matriz modelo × métricas (% fatales)

| Modelo | % obs. medio | R² | MAPE ajuste | MAPE hold-out | Bondad | ¿Razonable? |
| --- | --- | --- | --- | --- | --- | --- |
| Estacional | 0,66 % | 0,380 | 16,46 % | 21,96 % | moderado | si |
| Logit con exposición | 0,66 % | 0,362 | 15,23 % | 20,25 % | moderado | si |
| Ratio compuesto | 0,66 % | 0,376 | 16,13 % | 21,18 % | moderado | si |
| Media móvil | 0,66 % | 0,316 | 17,01 % | 35,09 % | bajo | no |
| OLS | 0,66 % | 0,006 | 21,81 % | 36,54 % | bajo | no |
| Logit-lineal | 0,66 % | 0,000 | 21,05 % | 35,48 % | bajo | no |
| ARIMA | 0,66 % | 0,000 | 24,54 % | 28,57 % | bajo | no |
| SARIMA | 0,66 % | 0,000 | 30,36 % | 34,26 % | bajo | no |

### 6.2 Mejor y peor modelo (MAPE hold-out)

- **Mejor:** Logit con exposición — MAPE hold-out 20,25 %
- **Peor:** OLS — MAPE hold-out 36,54 %

### 6.3 Interpretación

El % mensual de víctimas fatales es bajo (~0,66 %) y volátil; R² moderado (0,35–0,38) es **normal**. Logit con exposición y estacional sobre % lideran la prueba (~20–22 % MAPE). OLS, logit simple, ARIMA y SARIMA fallan en hold-out (>28 %); μ±3σ no aplica a porcentajes. Ratio compuesto enlaza con la lógica de conteos de la sección 1.


---

## 7. Sección 5 — Patrones día×hora y día de semana (P12/P13)

### 7.1 Matriz modelo × patrón temporal

| Modelo | Total horizonte | Celda líder P12 | Spearman P12 | Día líder P13 | Util |
| --- | --- | --- | --- | --- | --- |
| Estacional | 5530,96 | Martes 07:00 | 0,9992 | Martes | si |
| OLS | 5377,21 | Martes 07:00 | 0,9992 | Martes | si |
| Media móvil | 5189,01 | Martes 07:00 | 0,9992 | Martes | si |
| μ±3σ | 5260,08 | Martes 07:00 | 0,9992 | Martes | si |
| ARIMA | 4756,21 | Martes 07:00 | 0,9992 | Martes | si |
| SARIMA | 4572,92 | Martes 07:00 | 0,9989 | Martes | si |

### 7.2 Mejor y peor según total proyectado

- **Mayor total:** Estacional (5530,96 incidentes en horizonte)
- **Menor total:** SARIMA (4572,92 incidentes)

### 7.3 Interpretación

El **patrón relativo** (martes 07:00, martes en P13) es **idéntico** entre modelos (Spearman ≈ 0,999): el reparto temporal sigue el historial Laplace, no el modelo mensual. Lo que cambia es el **total** heredado de la sección 1 — coherente con el mejor/peor hold-out de §1. La utilidad operativa está en combinar «cuándo» (esta sección) con «dónde» (§3) y «cuánto» (§1).


---

## 8. Síntesis del caso de estudio A — decisiones recomendadas

| Sección | Pregunta | Mejor opción (escenario A) | Peor / evitar | Rol en la tesis |
| --- | --- | --- | --- | --- |
| 1 Proyección mensual | ¿Cuántos incidentes/mes? | SARIMA (MAPE hold-out 12,62 %) | Poisson / estacional (>22 % hold-out) | Ancla el volumen futuro |
| 2 Prioridad P05 | ¿Dónde priorizar según pasado? | Índice fijo — La Candelaria #1 | Barrio sin contraste # vol. | Contexto histórico |
| 3 Carga P08 | ¿Dónde se concentrará la carga? | μ±3σ ranking / estacional cifras | ARIMA (top erróneo) | Reparto territorial forward |
| 4 Proporción P07 | ¿Qué tan graves los meses? | Logit con exposición | Media móvil / OLS / SARIMA | Gravedad relativa |
| 5 Patrones P12/P13 | ¿Cuándo? | Patrón estable (martes 07:00) | N/A (mismo patrón) | Turnos y franjas |

**Cadena argumental:** §1 define el total → §3 lo reparte por comuna → §5 por día×hora; §2 y §4 aportan prioridad histórica y gravedad.

**μ±3σ en el caso A:** proyección 1753 inc./mes; hold-out 17,19 %; en §3 Spearman 0,9989.

**Total horizonte §5 (estacional):** 5530,96 incidentes en 3 meses sobre 75 088 observados en el periodo.


---

## 9. Resultados del caso de estudio (escenario A)

Resumen de hallazgos con los **mejores modelos por sección** según las métricas del tablero (MAPE hold-out en §1 y §4; Spearman y MAPE mediano territorial en §3). Periodo 2018–2021, incidentes ciudad, excluir COVID, horizonte y hold-out de 3 meses.

### 9.1 Proyección mensual (sección 1)

- **Mejor modelo:** SARIMA — MAPE hold-out **12,62 %** (precisión estimada **87,4 %**). Cumple el umbral adoptado (≤ 20 % MAPE).
- **Alternativa interpretable:** Media móvil — MAPE hold-out 15,71 % (precisión 84,3 %); mejor ajuste visual al historial (R² ≈ 0,6022).
- **Línea base μ±3σ:** proyección ≈ 1753 inc./mes; MAPE hold-out 17,19 %; 100 % meses dentro de μ±3σ.
- **Peor en prueba predictiva:** Poisson (MAPE hold-out 22,54 %). Buen MAPE de ajuste no garantiza buena proyección.

### 9.2 Prioridad territorial (sección 2 — P05)

- En el periodo se registraron **75088 incidentes** en **22 comunas**.
- **Líder del índice compuesto:** **La Candelaria** (índice 62,6, 12921 incidentes, nivel alto, puesto 1 por volumen).
- Top 3: La Candelaria; Castilla; Laureles Estadio.
- Describe el **pasado** (frecuencia, densidad, delta de promedios, gravedad, participación); complementa, no sustituye, las secciones prospectivas.

### 9.3 Carga territorial proyectada (sección 3 — P08/P09)

- **Mejor coherencia de ranking:** μ±3σ — Spearman **0,9989**; líder **La Candelaria** (906,45 inc. en horizonte).
- **Mejor precisión de cifras:** μ±3σ — MAPE mediano hold-out **21,29 %**.
- **Modelo adoptado:** estacional — carga #1 La Candelaria (982,2).
- **Evitar para ranking:** ARIMA — líder Sin Inf (utilidad parcial); Spearman 0,8001.

### 9.4 Proporción de víctimas fatales (sección 4 — P07)

- **% observado medio:** **0,66 %** (promedio mensual histórico; no depende del modelo).
- **Mejor modelo:** Logit con exposición — MAPE hold-out **20,25 %** (R² ajuste 0,362).
- **Peor en prueba:** OLS — MAPE hold-out 36,54 %.
- **Estacional**, **logit con exposición** y **ratio compuesto** permanecen en rango razonable (~20–22 %).

### 9.5 Patrones temporales (sección 5 — P12/P13)

- Con **SARIMA** (mejor §1), total horizonte **4572,92** incidentes.
- Franja líder **Martes 07:00**; día líder **Martes**; Spearman celdas **0,9989**.

### 9.6 Cuadro resumen de resultados

| Dimensión | Mejor enfoque | Indicador clave |
| --- | --- | --- |
| Volumen (§1) | SARIMA | MAPE hold-out 12,62 % |
| Prioridad pasado (§2) | Índice P05 | La Candelaria (índice 62,6) |
| Carga futura (§3) | Estacional / μ±3σ ranking | La Candelaria líder carga |
| Gravedad % (§4) | Logit con exposición | MAPE hold-out 20,25 % |
| Momento (§5) | Patrón histórico + total §1 | Martes 07:00 |

---

## 10. Conclusiones según los resultados

### 10.1 Conclusiones por bloque

1. **Proyección mensual.** **SARIMA** minimiza el error en hold-out (**12,62 %**) en el escenario A. Poisson y estacional no deben elegirse solo por el buen ajuste al gráfico. Media móvil y μ±3σ son alternativas válidas por simplicidad.

2. **Prioridad territorial.** P05 sintetiza el periodo histórico; **La Candelaria** lidera el índice compuesto. Esto orienta el diagnóstico del pasado, no el volumen proyectado de §3.

3. **Carga territorial.** **Estacional** mantiene a **La Candelaria** como comuna de mayor carga futura. **μ±3σ** mejora el ranking (Spearman ≈ 1); **ARIMA** altera el líder y no se recomienda.

4. **Proporción de fatales.** Gravedad mensual baja (~0,66 %); **Logit con exposición** obtiene el mejor hold-out (**20,25 %**). OLS y ARIMA/SARIMA sobre % no son adecuados.

5. **Patrones temporales.** El reparto (martes 07:00) es estable; el modelo de §1 solo define el total a distribuir en el horizonte.

### 10.2 Conclusión general

ViaData integra cinco perspectivas bajo un mismo periodo filtrado, con validación hold-out y comparación de modelos. Configuración recomendada (escenario A):

| Bloque | Decisión |
| --- | --- |
| §1 | **SARIMA** |
| §2 | Índice P05 (fórmula fija) |
| §3 | **Estacional** por comuna |
| §4 | **Logit con exposición** o estacional sobre % |
| §5 | Hereda §1 |

### 10.3 Limitaciones

- Proyecciones **exploratorias**, no predicción oficial ni intervalos de confianza.
- Hold-out de 3 meses favorece modelos estacionales; resultados cambian con 6 meses de prueba.
- Carga y % fatales: utilidad en **ranking y magnitud**, no en cifras exactas.
- Rangos cortos (< 24 meses) limitan SARIMA y series territoriales.

### 10.4 Aporte para la tesis

Los resultados fundamentan la utilidad del sistema: el analista puede articular **cuánto → dónde → cuándo**, con contexto de **prioridad histórica** y **gravedad**, eligiendo modelos con criterio hold-out documentado en los CSV de `evaluaciones/`.

