import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'
import {
  Area,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  fetchDashboardBarrios,
  fetchDashboardCatalogos,
  fetchDashboardCargaEsperadaTerritorial,
  fetchDashboardMatrizDiaHoraProyectada,
  fetchDashboardPorDiaSemanaProyectado,
  fetchDashboardPrediccionesMensuales,
  fetchDashboardPrioridadTerritorial,
  fetchDashboardProporcionFatalesMensual,
  fetchDashboardRangoFechas,
} from '../api/client.js'
import { PatronesDiaHoraPanel } from '../components/PatronesDiaHoraPanel.jsx'
import { GenerarReporteButton } from '../components/reportes/GenerarReporteButton.jsx'
import { RouteErrorBoundary } from '../components/RouteErrorBoundary.jsx'

async function fetchPrediccionesBundle({
  prediccionesQuery,
  prioridadQuery,
  proporcionQuery,
  cargaQuery,
  patronesQuery,
}) {
  const labels = [
    'proyección mensual',
    'prioridad territorial',
    'proporción de fatales',
    'carga esperada',
    'matriz día×hora proyectada',
    'día de semana proyectado',
  ]
  const tasks = [
    fetchDashboardPrediccionesMensuales(prediccionesQuery()),
    fetchDashboardPrioridadTerritorial(prioridadQuery()),
    fetchDashboardProporcionFatalesMensual(proporcionQuery()),
    fetchDashboardCargaEsperadaTerritorial(cargaQuery()),
    fetchDashboardMatrizDiaHoraProyectada(patronesQuery()),
    fetchDashboardPorDiaSemanaProyectado(patronesQuery()),
  ]
  const settled = await Promise.allSettled(tasks)
  const errors = []
  const pick = (i) => {
    const r = settled[i]
    if (r.status === 'fulfilled') return r.value
    errors.push(`${labels[i]}: ${r.reason?.message || r.reason}`)
    return null
  }
  return {
    predicciones: pick(0),
    prioridad: pick(1),
    proporcion: pick(2),
    cargaEsperada: pick(3),
    matrizProyectada: pick(4),
    diaSemanaProyectado: pick(5),
    errors,
  }
}

const FECHAS_REF_MEDE = {
  default_desde: '2021-01-01',
  default_hasta: '2021-09-30',
  selector_fecha_min: '2014-01-01',
  selector_fecha_max: '2021-09-30',
}

const LEGEND_TOP_PROPS = {
  verticalAlign: 'top',
  align: 'center',
  wrapperStyle: { fontSize: '12px', lineHeight: '16px', paddingBottom: 6 },
  iconType: 'circle',
}

const CHART_COMPACT_MAX_PX = 640

const MODELO_OPTS = [
  { value: 'ols', label: 'OLS (tendencia lineal)' },
  { value: 'estacional', label: 'Estacional (tendencia + mes calendario)' },
  { value: 'poisson', label: 'Poisson log-lineal' },
  { value: 'media_movil', label: 'Media móvil simple' },
  { value: 'arima', label: 'ARIMA (serie temporal, ≥12 meses)' },
  { value: 'sarima', label: 'SARIMA (estacional mensual, ≥24 meses)' },
]

const HOLDOUT_MESES_OPTS = [
  { value: 3, label: '3 meses' },
  { value: 6, label: '6 meses' },
]

const ARIMA_ORDER_DEFAULT = '2,1,3'
const SARIMA_SEASONAL_DEFAULT = '1,1,1,12'

function normalizeArimaOrderInput(s) {
  return String(s ?? '')
    .trim()
    .replace(/[()]/g, '')
}

function parseArimaTriple(s) {
  const parts = normalizeArimaOrderInput(s)
    .split(/[,;\s]+/)
    .filter(Boolean)
  if (parts.length !== 3) return null
  const nums = parts.map((p) => Number(p))
  if (nums.some((n) => !Number.isInteger(n) || n < 0 || n > 6)) return null
  return nums.join(',')
}

function parseSarimaSeasonal(s) {
  const parts = normalizeArimaOrderInput(s)
    .split(/[,;\s]+/)
    .filter(Boolean)
  if (parts.length !== 4) return null
  const nums = parts.map((p) => Number(p))
  if (nums.some((n) => Number.isNaN(n) || !Number.isInteger(n))) return null
  if (nums.slice(0, 3).some((n) => n < 0 || n > 6)) return null
  if (nums[3] !== 12) return null
  return nums.join(',')
}

function seasonalDraftCompleto(s) {
  return (
    normalizeArimaOrderInput(s)
      .split(/[,;\s]+/)
      .filter(Boolean).length >= 4
  )
}

function arimaParamsQuery(modelo, arimaOrder, sarimaSeasonal) {
  if (modelo !== 'arima' && modelo !== 'sarima') return {}
  const order = parseArimaTriple(arimaOrder)
  if (!order) return {}
  const q = { arima_order: order }
  if (modelo === 'sarima') {
    const seasonal = parseSarimaSeasonal(sarimaSeasonal)
    if (seasonal) q.sarima_seasonal = seasonal
  }
  return q
}

function ArimaParamFields({
  modelo,
  arimaOrder,
  sarimaSeasonal,
  onArimaOrderChange,
  onSarimaSeasonalChange,
  disabled = false,
}) {
  const [draftOrder, setDraftOrder] = useState(arimaOrder)
  const [draftSeasonal, setDraftSeasonal] = useState(sarimaSeasonal)

  useEffect(() => {
    setDraftOrder(arimaOrder)
    setDraftSeasonal(sarimaSeasonal)
  }, [arimaOrder, sarimaSeasonal, modelo])

  if (modelo !== 'arima' && modelo !== 'sarima') return null

  const orderInvalid = draftOrder.trim() !== '' && !parseArimaTriple(draftOrder)
  const seasonalInvalid =
    modelo === 'sarima' && draftSeasonal.trim() !== '' && !parseSarimaSeasonal(draftSeasonal)

  const commitOrder = () => {
    const parsed = parseArimaTriple(draftOrder)
    if (parsed) onArimaOrderChange(parsed)
    else setDraftOrder(arimaOrder)
  }

  const commitSeasonal = () => {
    const parsed = parseSarimaSeasonal(draftSeasonal)
    if (parsed) {
      onSarimaSeasonalChange(parsed)
    } else if (seasonalDraftCompleto(draftSeasonal)) {
      // Valor completo pero inválido (p. ej. periodo distinto de 12): restaurar el último válido
      setDraftSeasonal(sarimaSeasonal)
    }
    // Si aún está escribiendo (menos de 4 números), no forzar el valor por defecto
  }

  return (
    <>
      <label className="arima-param-field">
        Orden ARIMA (p,d,q)
        <input
          type="text"
          className={`predicciones-input arima-param-input${orderInvalid ? ' arima-param-input--invalid' : ''}`}
          value={draftOrder}
          disabled={disabled}
          placeholder={ARIMA_ORDER_DEFAULT}
          spellCheck={false}
          onChange={(e) => setDraftOrder(e.target.value)}
          onBlur={commitOrder}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              commitOrder()
            }
          }}
        />
      </label>
      {modelo === 'sarima' ? (
        <label className="arima-param-field">
          Estacional (P,D,Q,s)
          <input
            type="text"
            className={`predicciones-input arima-param-input${seasonalInvalid ? ' arima-param-input--invalid' : ''}`}
            value={draftSeasonal}
            disabled={disabled}
            placeholder={SARIMA_SEASONAL_DEFAULT}
            title="P, D y Q entre 0 y 6; s debe ser 12 (meses del año)"
            spellCheck={false}
            onChange={(e) => setDraftSeasonal(e.target.value)}
            onBlur={commitSeasonal}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                commitSeasonal()
              }
            }}
          />
        </label>
      ) : null}
    </>
  )
}

const VENTANA_MA_OPTS = [
  { value: 3, label: '3 meses' },
  { value: 6, label: '6 meses' },
  { value: 12, label: '12 meses' },
]

const VARIABLE_OPTS = [
  { value: 'incidentes', label: 'Incidentes' },
  { value: 'victimas', label: 'Víctimas' },
  { value: 'victimas_fatales', label: 'Víctimas fatales' },
]

const MODELO_PROP_PRINCIPAL = [
  { value: 'estacional', label: 'Estacional sobre % (recomendado)' },
  { value: 'logit_offset', label: 'Logit con exposición (víctimas/mes)' },
  { value: 'ratio_compuesto', label: 'Ratio compuesto (fatales÷víctimas proyectados)' },
  { value: 'media_movil', label: 'Media móvil simple' },
]

const MODELO_PROP_AVANZADO = [
  { value: 'ols', label: 'OLS sobre % mensual' },
  { value: 'logistica', label: 'Logit-lineal (tendencia en escala logit)' },
  { value: 'arima', label: 'ARIMA sobre % (≥12 meses válidos)' },
  { value: 'sarima', label: 'SARIMA sobre % (≥24 meses válidos)' },
]

const MODELO_PROP_OPTS = [...MODELO_PROP_PRINCIPAL, ...MODELO_PROP_AVANZADO]

const MODELO_CARGA_OPTS = [
  { value: 'estacional', label: 'Estacional (recomendado)' },
  { value: 'ols', label: 'OLS (tendencia)' },
  { value: 'media_movil', label: 'Media móvil simple' },
  { value: 'arima', label: 'ARIMA (≥12 meses)' },
  { value: 'sarima', label: 'SARIMA (≥24 meses)' },
]

const CARGA_CATEGORIA_COLOR = {
  alto: '#dc2626',
  medio: '#d97706',
  bajo: '#16a34a',
}

function buildCargaComparativaData(ranking, nivel) {
  return [...(ranking || [])]
    .sort((a, b) => (b.carga_proyectada_horizonte ?? 0) - (a.carga_proyectada_horizonte ?? 0))
    .slice(0, 12)
    .map((row) => {
      const nombre =
        nivel === 'barrio' ? (row.barrio_nombre ?? '—') : (row.comuna_nombre ?? '—')
      const etiqueta =
        nivel === 'barrio' && row.comuna_nombre ? `${nombre} (${row.comuna_nombre})` : nombre
      return {
        nombre: etiqueta,
        carga: Number(row.carga_proyectada_horizonte ?? 0),
        categoria: row.categoria_esperada ?? 'bajo',
        incidentes: row.incidentes_periodo ?? 0,
        rank: row.rank,
      }
    })
}

function serieObservados(r) {
  return r.observados ?? r.incidentes_observados ?? 0
}

function serieAjuste(r) {
  const v = r.ajuste_modelo ?? r.incidentes_ajuste_lineal
  return v != null ? v : null
}

function buildProporcionLineData(serieHistorica, proyeccion) {
  const h = (serieHistorica || []).map((r) => ({
    mes: r.mes_etiqueta,
    pct: r.pct_fatales,
    ajuste: r.ajuste_pct,
  }))
  let lastAjuste = null
  for (const row of h) {
    if (row.ajuste != null) lastAjuste = row.ajuste
  }
  if (h.length > 0 && h[h.length - 1].ajuste == null && lastAjuste != null) {
    h[h.length - 1] = { ...h[h.length - 1], ajuste: lastAjuste }
  }

  const pr = (proyeccion || []).map((r) => ({
    mes: r.mes_etiqueta,
    pct: null,
    ajuste: r.pct_fatales_proyectado ?? r.ajuste_pct,
    bandaInf: r.pct_banda_inf ?? null,
    bandaSup: r.pct_banda_sup ?? null,
  }))
  if (pr.length > 0 && h.length > 0) {
    const ultimoHist = h[h.length - 1].ajuste
    if (
      ultimoHist != null &&
      pr[0].ajuste != null &&
      pr[0].ajuste === 0 &&
      ultimoHist > 0
    ) {
      pr[0] = { ...pr[0], ajuste: ultimoHist }
    }
  }
  return [...h, ...pr]
}

function buildPrediccionesLineData(serieHistorica, proyeccion) {
  const h = (serieHistorica || []).map((r) => ({
    mes: r.mes_etiqueta,
    observados: serieObservados(r),
    ajuste: serieAjuste(r),
  }))
  const pr = (proyeccion || []).map((r) => ({
    mes: r.mes_etiqueta,
    observados: null,
    ajuste: serieAjuste(r),
  }))
  return [...h, ...pr]
}

function modeloLegendLabel(modelo) {
  if (modelo === 'estacional') return 'Modelo estacional + extrapolación'
  if (modelo === 'poisson') return 'Modelo Poisson + extrapolación'
  if (modelo === 'media_movil') return 'Media móvil + extrapolación'
  if (modelo === 'arima') return 'ARIMA + extrapolación'
  if (modelo === 'sarima') return 'SARIMA + extrapolación'
  return 'Tendencia OLS + extrapolación'
}

function minMesesModelo(modelo, ventanaMeses) {
  if (modelo === 'ols') return 'dos'
  if (modelo === 'logit_offset' || modelo === 'ratio_compuesto') return 'tres'
  if (modelo === 'media_movil' && ventanaMeses) return String(ventanaMeses)
  if (modelo === 'arima') return '12'
  if (modelo === 'sarima') return '24'
  return 'tres'
}

function ventanaMaQuery(modelo, ventana) {
  return modelo === 'media_movil' ? { ventana_ma: ventana } : {}
}

function SeccionModeloToolbar({
  modelo,
  onModeloChange,
  opciones,
  ventanaMa,
  onVentanaMaChange,
  horizonte,
  onHorizonteChange,
  loading = false,
  horizonteId,
  arimaOrder,
  onArimaOrderChange,
  sarimaSeasonal,
  onSarimaSeasonalChange,
  children = null,
}) {
  return (
    <div className="predicciones-toolbar seccion-modelo-toolbar">
      <label>
        Modelo
        <select
          className="predicciones-select"
          value={modelo}
          disabled={loading}
          onChange={(e) => onModeloChange(e.target.value)}
        >
          {opciones.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
      {modelo === 'media_movil' && ventanaMa != null && onVentanaMaChange && (
        <label>
          Ventana MA
          <select
            className="predicciones-select"
            value={ventanaMa}
            disabled={loading}
            onChange={(e) => onVentanaMaChange(Number(e.target.value))}
          >
            {VENTANA_MA_OPTS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>
      )}
      <ArimaParamFields
        modelo={modelo}
        arimaOrder={arimaOrder}
        sarimaSeasonal={sarimaSeasonal}
        onArimaOrderChange={onArimaOrderChange}
        onSarimaSeasonalChange={onSarimaSeasonalChange}
        disabled={loading}
      />
      {horizonte != null && onHorizonteChange && (
        <label>
          Horizonte (meses)
          <select
            id={horizonteId}
            className="predicciones-select"
            value={String(horizonte)}
            disabled={loading}
            onChange={(e) =>
              onHorizonteChange(Math.min(12, Math.max(1, Number(e.target.value) || 3)))
            }
          >
            {Array.from({ length: 12 }, (_, i) => i + 1).map((n) => (
              <option key={n} value={String(n)}>
                {n}
              </option>
            ))}
          </select>
        </label>
      )}
      {children}
    </div>
  )
}

function metricasBondad(c) {
  if (c?.r2 == null || c?.r2 === undefined) return null
  return (
    <>
      R² ≈ <strong>{c.r2}</strong>
      {c.rmse != null && (
        <>
          , RMSE ≈ <strong>{c.rmse}</strong>
        </>
      )}
      {c.mape_pct != null && (
        <>
          , MAPE ≈ <strong>{c.mape_pct}%</strong>
        </>
      )}
    </>
  )
}

const BONDAD_METRICAS_GLOSARIO = [
  {
    sigla: 'R² (R cuadrado)',
    texto:
      'Indica qué tan bien el modelo sigue los datos del periodo, de 0 a 1. ' +
      'Cerca de 1 significa que reproduce bien la serie; cerca de 0, que casi no captura la variación. ' +
      'Solo mide el ajuste sobre el historial, no garantiza que la proyección futura sea acertada.',
  },
  {
    sigla: 'RMSE',
    texto:
      'Error típico en las mismas unidades de la serie: incidentes o víctimas en conteos, puntos porcentuales en % fatales. ' +
      'Cuanto más bajo, mejor.',
  },
  {
    sigla: 'MAPE',
    texto:
      'Error medio expresado como porcentaje del valor real. ' +
      'Un MAPE de 15 % significa que, en promedio, la predicción se aleja alrededor de un 15 % del dato observado.',
  },
  {
    sigla: 'Precisión estimada',
    texto:
      'Lectura sencilla del MAPE: 100 % menos el error. ' +
      'Si el MAPE es 15 %, la precisión estimada ronda el 85 %. Sirve para comparar modelos de un vistazo.',
  },
  {
    sigla: 'Prueba con meses reservados',
    texto:
      'El sistema aparta los últimos 3 o 6 meses, entrena sin ellos y ve qué habría predicho. ' +
      'Así se comprueba si el modelo anticipa bien meses que aún no «vio» al ajustar. ' +
      'Es más fiable que mirar solo el ajuste sobre todo el historial.',
  },
  {
    sigla: 'AIC y BIC',
    texto:
      'Sirven para comparar ARIMA y SARIMA entre sí. Valores más bajos suelen indicar mejor equilibrio entre ajuste y complejidad.',
  },
]

function BondadMetricasContenido({ umbralesP07 = null, mostrarReglaPractica = true }) {
  return (
    <>
      <p>
        Estas cifras aparecen bajo los gráficos. Ayudan a comparar modelos y a saber si la proyección es razonable
        con los filtros elegidos; no son una predicción exacta mes a mes.
      </p>
      <ul className="bondad-metricas-list">
        {BONDAD_METRICAS_GLOSARIO.map((item) => (
          <li key={item.sigla}>
            <strong>{item.sigla}:</strong> {item.texto}
          </li>
        ))}
      </ul>
      {umbralesP07 && (
        <p>
          <strong>En proporción de fatales:</strong> un R² «moderado» (entre 0,35 y 0,55) es lo habitual;
          no interprete R² bajo como fallo del sistema si la <strong>prueba con meses reservados</strong>{' '}
          es razonable. Los modelos <strong>estacional</strong>, <strong>logit con exposición</strong> y{' '}
          <strong>ratio compuesto</strong> son los que conviene comparar primero.
        </p>
      )}
      {!umbralesP07 && (
        <>
          <p>
            <strong>Dos lecturas distintas:</strong>
          </p>
          <ul className="bondad-metricas-list">
            <li>
              <strong>Ajuste al historial</strong> (R² y MAPE bajo el gráfico): qué tan bien el modelo reproduce los
              meses que ya conoce. Un R² alto aquí no basta para confiar en los meses futuros.
            </li>
            <li>
              <strong>Prueba con meses reservados</strong> (panel más abajo): el modelo predice unos meses recientes sin
              haberlos usado al entrenar. Ahí conviene mirar el MAPE y la precisión estimada antes de elegir modelo.
            </li>
          </ul>
          <p>
            <strong>R² en conteos mensuales:</strong> por encima de 0,55 suele ser un buen ajuste; entre 0,35 y 0,54,
            moderado; por debajo de 0,35, bajo. Con estacionalidad y el periodo COVID es normal no acercarse a 1.
          </p>
          <p>
            <strong>Precisión aceptable:</strong> en la prueba con meses reservados, un MAPE de 20 % o menos equivale
            a una precisión estimada de al menos 80 %. Por encima de ese error, conviene probar otro modelo o ampliar
            el rango de fechas.
          </p>
        </>
      )}
      {mostrarReglaPractica && (
        <p>
          <strong>En la práctica:</strong> mire R² y MAPE juntos. Si ambos son malos, pruebe otro modelo, amplíe fechas
          o use la proyección solo como referencia de magnitud, no como cifra exacta.
        </p>
      )}
    </>
  )
}

function BondadMetricasGuia({ meta = null, defaultOpen = false, incluirHoldout = false }) {
  return (
    <details className="prioridad-ayuda-details bondad-metricas-guia" open={defaultOpen}>
      <summary>
        {incluirHoldout
          ? '¿Qué significan estas métricas?'
          : '¿Qué significan R², RMSE, MAPE, AIC y BIC?'}
      </summary>
      <div className="muted small bondad-metricas-body">
        <BondadMetricasContenido umbralesP07={meta?.umbrales_r2_p07} />
        {incluirHoldout ? (
          <p>
            Más detalle sobre la <strong>prueba con meses reservados</strong> y cómo elegir el rango de fechas está en
            el panel «Prueba del modelo» (debajo del gráfico).
          </p>
        ) : null}
      </div>
    </details>
  )
}

function BondadConsejoModelo({ meta }) {
  const c = meta?.coeficientes
  if (!c || meta?.sin_modelo) return null
  const r2 = Number(c.r2)
  const mape = c.mape_pct != null ? Number(c.mape_pct) : null
  const mod = meta.modelo
  const esP07 = meta?.min_victimas_mes != null || meta?.umbrales_r2_p07 != null
  const hold = meta?.holdout
  const mapeHold = hold?.activo && hold.mape_pct != null ? Number(hold.mape_pct) : null
  const precisionHold = mapeHold != null ? precisionDesdeMape(mapeHold) : null
  const holdoutBueno = precisionHold != null && precisionHold >= 80
  const holdoutMalo = mapeHold != null && mapeHold > 20
  if (Number.isNaN(r2)) return null

  if (holdoutBueno && r2 < 0.35) {
    return (
      <p className="muted small bondad-consejo bondad-consejo--ok" role="status">
        <strong>Lectura rápida:</strong> el R² del ajuste es bajo, pero la{' '}
        <strong>prueba con meses reservados</strong> es aceptable (precisión estimada ≈ {precisionHold} %).
        En ARIMA/SARIMA es habitual: priorice la prueba para decidir si usa este modelo.
      </p>
    )
  }

  if (holdoutMalo && r2 >= 0.5 && mape != null && mape <= 15) {
    return (
      <p className="warn small bondad-consejo" role="status">
        <strong>Lectura rápida:</strong> el ajuste al historial se ve bueno, pero la prueba con meses reservados
        sale peor (MAPE ≈ {mapeHold} %). Conviene probar <strong>estacional</strong>, <strong>media móvil</strong>{' '}
        o <strong>SARIMA</strong> antes de confiar en esta proyección.
      </p>
    )
  }

  if (holdoutBueno && r2 >= 0.35) {
    return (
      <p className="muted small bondad-consejo bondad-consejo--ok" role="status">
        <strong>Lectura rápida:</strong> ajuste y prueba con meses reservados coherentes (precisión estimada ≈{' '}
        {precisionHold} %). La proyección es una referencia razonable con los filtros actuales.
      </p>
    )
  }

  if (r2 < 0.35) {
    if (esP07 && (mod === 'arima' || mod === 'sarima' || mod === 'ols' || mod === 'logistica')) {
      return (
        <p className="warn small bondad-consejo" role="status">
          <strong>Lectura rápida:</strong> R² cercano a 0 indica que este modelo no está capturando bien la
          variación del % mensual. MAPE {mape != null && mape > 20 ? `elevado (${mape} %)` : 'también conviene revisarlo'}.
          Para P07 pruebe <strong>Estacional</strong>, <strong>Logit con exposición</strong> o{' '}
          <strong>Ratio compuesto</strong>. OLS/ARIMA en % volátil suelen dejar R² bajo.
        </p>
      )
    }
    return (
      <p className="warn small bondad-consejo" role="status">
        <strong>Lectura rápida:</strong> ajuste bajo (R² &lt; 0,35). Pruebe modelo <strong>estacional</strong>, amplíe
        el rango de fechas o active <strong>Excluir mar–ago 2020</strong> antes de usar la proyección con confianza.
      </p>
    )
  }

  if (r2 >= 0.35 && r2 < 0.55 && mape != null && mape > 20) {
    return (
      <p className="muted small bondad-consejo" role="status">
        <strong>Lectura rápida:</strong> R² moderado pero MAPE elevado — el modelo capta parte del patrón, pero mes a
        mes puede alejarse bastante del dato observado. Úselo para tendencia u orden de magnitud, no para cifras exactas.
      </p>
    )
  }

  if (r2 >= 0.55) {
    return (
      <p className="muted small bondad-consejo bondad-consejo--ok" role="status">
        <strong>Lectura rápida:</strong> ajuste consistente en el periodo elegido. Aun así, recuerde que la proyección
        futura es un escenario modelado, no un hecho observado.
      </p>
    )
  }

  return null
}

function nivelBondadLabel(nivel) {
  if (nivel === 'bueno') return 'buena'
  if (nivel === 'bajo') return 'baja'
  return 'moderada'
}

function CargaBondadPanel({ meta }) {
  const b = meta?.bondad_agregada
  if (!b || meta?.sin_datos) return null
  const nivelRanking = b.nivel_confianza_ranking || b.nivel_confianza || 'moderado'
  const nivelCifras = b.nivel_confianza_cifras || 'bajo'
  const bondadClass =
    nivelRanking === 'bueno' ? 'bueno' : nivelRanking === 'bajo' ? 'bajo' : 'moderado'
  const precision = b.precision_estimada_mediana_pct
  const fmtSpearman =
    b.spearman_carga_frecuencia != null
      ? String(b.spearman_carga_frecuencia).replace('.', ',')
      : null
  const recs = b.recomendaciones_mejora || []

  return (
    <div className="carga-bondad-panel">
      <p className={`proporcion-bondad-resumen bondad-${bondadClass}`}>
        <strong>Confianza del ranking (P08/P09):</strong> {nivelBondadLabel(nivelRanking)}
        {fmtSpearman != null && (
          <>
            {' '}
            · Spearman carga↔volumen: <strong>{fmtSpearman}</strong>
          </>
        )}
        {b.top1_rank_frecuencia != null && (
          <>
            {' '}
            · #1 carga = #{b.top1_rank_frecuencia} por volumen
          </>
        )}
      </p>
      <p className={`muted small bondad-consejo ${nivelCifras === 'bajo' ? '' : 'bondad-consejo--ok'}`}>
        <strong>Confianza de cifras absolutas:</strong> {nivelBondadLabel(nivelCifras)}
        {b.mediana_mape_holdout_pct != null && (
          <>
            {' '}
            · MAPE mediano en prueba: <strong>{b.mediana_mape_holdout_pct} %</strong>
            {precision != null && ` (≈ ${precision} % precisión)`}
          </>
        )}
        {b.mape_ponderado_incidentes_pct != null && (
          <> · MAPE ponderado: <strong>{b.mape_ponderado_incidentes_pct} %</strong></>
        )}
        {b.mediana_mape_nucleo_pct != null && b.territorios_nucleo_bondad > 0 && (
          <>
            {' '}
            · núcleo ≥{b.min_incidentes_nucleo ?? 1000} inc.: <strong>{b.mediana_mape_nucleo_pct} %</strong>
          </>
        )}
        {b.pct_territorios_holdout_aceptable != null && (
          <>
            {' '}
            · {b.pct_territorios_holdout_aceptable} % territorios ≤ {b.umbral_mape_aceptable_pct ?? 20} % MAPE
          </>
        )}
      </p>
      {b.nota_limitacion_territorial && (
        <p className="muted small">{b.nota_limitacion_territorial}</p>
      )}
      <p className="muted small">
        Proyección en <strong>{b.territorios_proyectables}</strong> de{' '}
        <strong>{b.territorios_totales_periodo}</strong> territorios
        {b.territorios_con_holdout != null
          ? ` (${b.territorios_con_holdout} con prueba hold-out).`
          : '.'}
      </p>
      {b.interpretacion && (
        <p className={`bondad-interpretacion bondad-${bondadClass}`} role="status">
          <strong>Interpretación:</strong> {b.interpretacion}
        </p>
      )}
      {recs.length > 0 && (
        <details className="prioridad-ayuda-details carga-modelo-ayuda">
          <summary>¿Por qué el MAPE es alto y qué puedo hacer?</summary>
          <ul className="muted small carga-recomendaciones-list">
            {recs.map((t) => (
              <li key={t}>{t}</li>
            ))}
          </ul>
        </details>
      )}
      <details className="prioridad-ayuda-details carga-modelo-ayuda">
        <summary>¿Cómo elegir el mejor modelo aquí?</summary>
        <div className="muted small">
          <p>{b.guia_eleccion_modelo}</p>
          <p>
            <strong>No hace falta otro tipo de modelo</strong> (clasificación/regresión distinta) para P08: la
            categoría alto/medio/bajo ya es una clasificación relativa por terciles. Lo que importa es si el{' '}
            <em>orden</em> entre territorios es estable (Spearman, # vol.).
          </p>
          <p>
            <strong>Para mejorar cifras:</strong> use comuna (no barrio), estacional u OLS, rango largo (2018–2021),
            excluir COVID. Modelos jerárquicos o reparto proporcional desde la sección 1 serían un trabajo futuro.
          </p>
        </div>
      </details>
    </div>
  )
}

const PRIORIDAD_COLUMNAS_AYUDA = [
  {
    col: '#',
    titulo: 'Posición (#)',
    texto: 'Orden del ranking según la vista elegida (índice compuesto o solo frecuencia).',
  },
  {
    col: '# vol.',
    titulo: 'Puesto por volumen',
    texto: 'Posición si ordenara únicamente por número de incidentes en el periodo.',
  },
  {
    col: 'Territorio',
    titulo: 'Comuna o barrio',
    texto: 'Nombre del territorio evaluado (barrio muestra también la comuna entre paréntesis).',
  },
  {
    col: 'Índice',
    titulo: 'Índice compuesto',
    texto:
      'Puntaje que combina frecuencia, densidad/km², tendencia, % fatales y participación (scores 0–100). No es el número de incidentes.',
  },
  {
    col: 'Nivel',
    titulo: 'Nivel de prioridad',
    texto:
      'Alto / medio / bajo según terciles del índice entre los territorios elegibles (comparación relativa).',
  },
  {
    col: 'Incidentes',
    titulo: 'Incidentes en el periodo',
    texto: 'Conteo de incidentes distintos entre las fechas «Desde» y «Hasta» (y filtros aplicados).',
  },
  {
    col: 'Dens./km²',
    titulo: 'Densidad de incidentes',
    texto: 'Incidentes por km² según el área del polígono oficial de la comuna o barrio.',
  },
  {
    col: '% fatales',
    titulo: '% víctimas fatales',
    texto: 'Porcentaje de víctimas en ese territorio clasificadas como fatales (misma regla que los KPIs).',
  },
  {
    col: 'Delta prom.',
    titulo: 'Delta de promedios mensuales',
    texto:
      'Por territorio: promedio de los últimos meses menos promedio del tramo anterior (ventana 6 meses si hay ≥ 12 meses en el periodo). Positivo = empeora. Solo valores ≥ 0 suman al índice; si el volumen es bajo, el score de tendencia se atenúa.',
  },
  {
    col: 'Part. %',
    titulo: 'Participación %',
    texto: 'Porcentaje de todos los incidentes del periodo filtrado que ocurrieron en este territorio.',
  },
  {
    col: 'Componentes',
    titulo: 'Abreviaturas (scores 0–100)',
    texto: 'Freq, Dens, Tend, Fatal y Part: puntuación relativa de cada dimensión. Cómo leerlas → guía «Scores y índice».',
  },
]

const PRIORIDAD_COMPONENTES_PILLS = [
  {
    sigla: 'Freq',
    clave: 'frecuencia_incidentes',
    titulo: 'Frecuencia',
    texto: 'Qué tan alto es el volumen de incidentes frente al resto de territorios del mismo nivel. 100 = el más alto del ranking.',
  },
  {
    sigla: 'Dens',
    clave: 'densidad_km2',
    titulo: 'Densidad',
    texto: 'Incidentes por km² (polígono oficial). 100 = la mayor concentración espacial entre los elegibles.',
  },
  {
    sigla: 'Tend',
    clave: 'tendencia_mensual',
    titulo: 'Tendencia',
    texto:
      'Delta de promedios mensuales (columna «Delta prom.»), comparado entre territorios. Solo cuenta si el delta ≥ 0. 100 = el que más empeora en el periodo.',
  },
  {
    sigla: 'Fatal',
    clave: 'pct_victimas_fatales',
    titulo: 'Gravedad',
    texto: '% de víctimas fatales en ese territorio, frente a los demás. 100 = el mayor % relativo (no el mayor conteo absoluto).',
  },
  {
    sigla: 'Part',
    clave: 'participacion',
    titulo: 'Participación',
    texto: 'Peso proporcional en el total de incidentes del periodo filtrado. Suele ir de la mano con Freq.',
  },
]

function PrioridadAlertaLiderazgo({ meta }) {
  const alerta = meta?.alerta_liderazgo
  if (!alerta?.mensaje) return null
  return (
    <p className="warn small prioridad-alerta-liderazgo" role="status">
      {alerta.mensaje}
    </p>
  )
}

function PrioridadNotasContexto({ meta }) {
  if (!meta) return null
  return (
    <div className="prioridad-notas-contexto muted small">
      {meta.nota_tablero_vs_p05 && <p>{meta.nota_tablero_vs_p05}</p>}
      {meta.nota_complemento_carga_esperada && (
        <p>
          {meta.nota_complemento_carga_esperada.replace(
            'sección 3',
            'sección 3 (más abajo en esta página)',
          )}
        </p>
      )}
    </div>
  )
}

function PrioridadSensibilidadAyuda({ meta }) {
  const s = meta?.sensibilidad_pesos
  if (!s?.variantes?.length) return null
  return (
    <details className="prioridad-ayuda-details">
      <summary>Estabilidad del top 5 ante otros pesos</summary>
      <p className="muted small">{s.interpretacion}</p>
      <ul className="prioridad-pesos-list muted small">
        {s.variantes.map((v) => (
          <li key={v.variante}>
            <strong>{v.variante.replace(/_/g, ' ')}</strong>: {v.coincidencias_con_base} de 5 territorios
            coinciden con el ranking base.
          </li>
        ))}
      </ul>
    </details>
  )
}

function nombreTerritorioPrioridad(row, nivel) {
  if (!row) return '—'
  if (nivel === 'barrio') {
    const barrio = row.barrio_nombre?.trim()
    const comuna = row.comuna_nombre?.trim()
    if (barrio && comuna) return `${barrio} (${comuna})`
    if (barrio) return barrio
    if (comuna) return comuna
    return '—'
  }
  return row.comuna_nombre?.trim() || '—'
}

function filasPrioridadTabla(prioridad, ordenPrioridad) {
  if (!prioridad?.ranking?.length) return []
  if (ordenPrioridad === 'frecuencia') {
    const base =
      prioridad.ranking_por_frecuencia?.length > 0
        ? prioridad.ranking_por_frecuencia
        : [...prioridad.ranking].sort(
            (a, b) => (a.rank_frecuencia ?? 99) - (b.rank_frecuencia ?? 99),
          )
    return base.map((row, i) => ({
      ...row,
      rank: i + 1,
      rank_frecuencia: row.rank_frecuencia ?? i + 1,
    }))
  }
  return prioridad.ranking
}

function PrioridadComponentesCelda({ componentes, tendenciaAtenuada }) {
  if (!componentes) return '—'
  return (
    <span className="prioridad-comp-scores" aria-label="Scores por componente; ver guía Scores y índice">
      {PRIORIDAD_COMPONENTES_PILLS.map(({ sigla, clave }) => (
        <span key={clave} className="prioridad-comp-pill">
          {sigla} {componentes[clave] ?? '—'}
        </span>
      ))}
      {tendenciaAtenuada ? (
        <span className="prioridad-comp-pill prioridad-comp-atenuada" title="Tendencia atenuada por bajo volumen">
          ↓
        </span>
      ) : null}
    </span>
  )
}

function prioridadAporteComponente(score, peso) {
  if (score == null || peso == null) return null
  return Math.round(score * peso * 100) / 100
}

function PrioridadInterpretacionComponentesGuia({ meta, filaLider, nivel }) {
  const pesos = meta?.pesos
  if (!pesos) return null
  const pct = (k) => `${Math.round((pesos[k] ?? 0) * 100)} %`

  return (
    <details className="prioridad-ayuda-details prioridad-componentes-guia">
      <summary>Scores y índice — cómo leer Freq, Dens, Tend, Fatal y Part</summary>
      <div className="muted small prioridad-componentes-guia-body">
        <p>
          Los valores de la columna <strong>Componentes</strong> no son incidentes ni porcentajes del periodo: son
          puntajes <strong>0–100</strong> que comparan cada territorio con los demás del mismo nivel (comuna o barrio)
          en el rango y filtros actuales. El <strong>Índice</strong> es la suma ponderada de esos cinco scores.
        </p>
        <dl className="prioridad-columnas-dl">
          {PRIORIDAD_COMPONENTES_PILLS.map((p) => (
            <div key={p.clave} className="prioridad-dl-row">
              <dt>
                <span className="prioridad-comp-pill prioridad-comp-pill-inline">{p.sigla}</span> {p.titulo}{' '}
                <span className="prioridad-peso-inline">({pct(p.clave)})</span>
              </dt>
              <dd>{p.texto}</dd>
            </div>
          ))}
        </dl>
        <p>
          <strong>Fórmula:</strong> Índice ≈ {pct('frecuencia_incidentes')}×Freq + {pct('densidad_km2')}×Dens +{' '}
          {pct('tendencia_mensual')}×Tend + {pct('pct_victimas_fatales')}×Fatal + {pct('participacion')}×Part.
        </p>
        <p>
          <strong>Lectura rápida:</strong> si Freq, Dens y Part están cerca de 100, el territorio lidera por{' '}
          <em>tamaño y concentración</em>. Si Tend o Fatal dominan con Freq bajo, puede subir en el ranking por{' '}
          <em>empeoramiento reciente o gravedad</em> aunque no sea el más grande. La etiqueta <strong>↓</strong> en
          Componentes indica que la tendencia fue atenuada por bajo volumen.
        </p>
        {filaLider?.componentes_normalizados && (
          <div className="prioridad-ejemplo-lider">
            <p>
              <strong>Ejemplo con el #1 actual</strong> ({nombreTerritorioPrioridad(filaLider, nivel)}): índice{' '}
              <strong>{filaLider.indice_prioridad}</strong>
              {filaLider.rank_frecuencia != null && filaLider.rank_frecuencia !== 1 ? (
                <>
                  {' '}
                  — puesto <strong>{filaLider.rank_frecuencia}</strong> por volumen (# vol.), por eso conviene
                  contrastar con «Solo por frecuencia».
                </>
              ) : (
                <> — también lidera por volumen (# vol.).</>
              )}
            </p>
            <ul className="prioridad-pesos-list">
              {PRIORIDAD_COMPONENTES_PILLS.map(({ sigla, clave, titulo }) => {
                const score = filaLider.componentes_normalizados[clave]
                const aporte = prioridadAporteComponente(score, pesos[clave])
                if (score == null) return null
                return (
                  <li key={clave}>
                    <strong>{sigla}</strong> {score} → aporta ~{aporte ?? '—'} pts al índice ({titulo.toLowerCase()})
                  </li>
                )
              })}
            </ul>
          </div>
        )}
      </div>
    </details>
  )
}

function PrioridadPesosAyuda({ meta }) {
  const items = meta?.justificacion_pesos
  const tend = meta?.tendencia_componente
  if (!items?.length) return null
  return (
    <details className="prioridad-ayuda-details">
      <summary>¿Por qué estos pesos y el delta de promedios?</summary>
      <ul className="prioridad-pesos-list muted small">
        {items.map((it) => (
          <li key={it.componente}>
            <strong>{Math.round(it.peso * 100)} %</strong> — {it.componente.replace(/_/g, ' ')}:{' '}
            {it.motivo}
          </li>
        ))}
      </ul>
      {tend && (
        <div className="muted small prioridad-ols-nota">
          <p>
            <strong>Tendencia en la tabla:</strong> {tend.etiqueta}. {tend.por_que_delta ?? tend.por_que_ols}
          </p>
          <p>
            <strong>¿Por qué no estacional aquí?</strong> {tend.por_que_no_estacional}
          </p>
        </div>
      )}
    </details>
  )
}

function PrioridadColumnasAyuda() {
  return (
    <details className="prioridad-ayuda-details">
      <summary>Cómo interpretar cada columna de la tabla</summary>
      <dl className="prioridad-columnas-dl">
        {PRIORIDAD_COLUMNAS_AYUDA.map((item) => (
          <div key={item.col} className="prioridad-dl-row">
            <dt>{item.titulo}</dt>
            <dd>{item.texto}</dd>
          </div>
        ))}
      </dl>
    </details>
  )
}

function PrediccionesFiltrosGuia() {
  return (
    <details className="prioridad-ayuda-details page-intro-guide">
      <summary>Guía para configurar los filtros</summary>
      <div className="page-intro-guide-body muted small">
        <p>
          Los filtros del panel superior aplican a <strong>todos</strong> los bloques (fechas, territorio,
          variable y exclusión COVID). Cada sección de predicción tiene su <strong>propio modelo</strong> y
          horizonte; al cambiarlos se recalcula solo ese bloque. Tras cambiar filtros compartidos, pulse{' '}
          <strong>Actualizar</strong>.
        </p>
        <ul>
          <li>
            <strong>Desde / Hasta:</strong> periodo histórico que alimenta el ajuste. Por defecto se carga el{' '}
            <strong>último año con registros</strong>. Conviene al menos unos meses de historia; modelos estacionales
            o por clase piden series más largas.
          </li>
          <li>
            <strong>Comuna, barrio y clase:</strong> acotan el análisis. Deje «Todas» / «Todos» para ver la ciudad
            completa (respetando el resto de filtros).
          </li>
          <li>
            <strong>Territorio:</strong> <em>Registro Mede</em> usa comuna/barrio del expediente;{' '}
            <em>Polígono PostGIS</em> usa la ubicación espacial del punto en el mapa.
          </li>
          <li>
            <strong>Variable:</strong> qué magnitud se proyecta en la sección de proyección mensual (incidentes,
            víctimas o víctimas fatales). Las demás secciones tienen su propia lógica (%, carga, patrones).
          </li>
          <li>
            <strong>Excluir mar–ago 2020:</strong> omite esos meses del ajuste por el confinamiento COVID, sin
            cambiar el rango visible del gráfico.
          </li>
          <li>
            <strong>Modelo por sección:</strong> la proyección mensual (bloque 1), la proporción de fatales
            (bloque 4) y la carga territorial (bloque 3) tienen selector de modelo propio. Los patrones día×hora
            y día de semana (bloque 5) reutilizan el modelo y horizonte del bloque 1 para el total de
            incidentes a repartir.
          </li>
        </ul>
        <p>
          <strong>Elegir modelo y fechas (proyección mensual)</strong>
        </p>
        <ul>
          <li>
            <strong>Rango de fechas:</strong> con más meses (por ejemplo 2018–2021) los modelos captan mejor la
            estacionalidad. Con pocos meses algunos modelos no se activan o dan resultados inestables.
          </li>
          <li>
            <strong>Meses de prueba:</strong> en la sección 1 puede reservar 3 o 6 meses al final del periodo. El
            panel «Prueba del modelo» muestra qué tan bien habría anticipado esos meses.
          </li>
          <li>
            <strong>Qué mirar:</strong> compare el ajuste bajo el gráfico con la prueba de meses reservados. Si el
            ajuste se ve muy bueno pero la prueba sale mal, ese modelo no es el más adecuado.
          </li>
        </ul>
        <p>
          <strong>Consejos para elegir el modelo</strong>
        </p>
        <ul>
          <li>
            <strong>Proyección mensual:</strong>
            <ul>
              <li>
                <strong>Estacional</strong> — buen punto de partida si hay al menos un año de historia: captura meses
                altos/bajos (vacaciones, fin de año, etc.) además de la tendencia.
              </li>
              <li>
                <strong>OLS</strong> — serie corta o solo le interesa una recta de tendencia; no reproduce picos
                mensuales. Útil para una lectura rápida con pocos meses (mín. 2).
              </li>
              <li>
                <strong>Poisson</strong> — conteos mensuales (sobre todo <strong>incidentes</strong>); adecuado cuando
                los valores son enteros pequeños o moderados. Si la serie es muy irregular, compare con estacional.
              </li>
              <li>
                <strong>Media móvil</strong> — extrapola «como los últimos k meses» (3, 6 o 12); suaviza ruido y evita
                extrapolar tendencias fuertes. Requiere al menos k meses en el ajuste.
              </li>
              <li>
                <strong>ARIMA</strong> — modela la dependencia temporal mes a mes (memoria de corto plazo y tendencia
                con diferenciación). Requiere al menos <strong>12 meses</strong> con datos en el rango. Útil cuando OLS
                o la media móvil no capturan bien la dinámica de la serie.
              </li>
              <li>
                <strong>SARIMA</strong> — como ARIMA, pero con estacionalidad mensual (ciclo de 12 meses). Requiere al
                menos <strong>24 meses</strong> (dos años completos) para estimar el patrón estacional con estabilidad.
                Compare con <strong>Estacional</strong> si prefiere un modelo más interpretable con menos historia.
              </li>
            </ul>
          </li>
          <li>
            <strong>Proporción de fatales:</strong> empiece por <strong>Estacional sobre %</strong>. Si el
            volumen de víctimas cambia mucho entre meses, pruebe <strong>Logit con exposición</strong>; si
            prefiere enlazar con la proyección de conteos, <strong>Ratio compuesto</strong>. Use la{' '}
            <strong>prueba con meses reservados</strong> para decidir; el R² del gráfico suele ser modesto
            y eso es normal en porcentajes tan pequeños. Los modelos avanzados (OLS, ARIMA…) rara vez aportan aquí.
          </li>
          <li>
            <strong>Carga territorial:</strong> <strong>Estacional</strong> (recomendado) si proyecta
            varios meses y espera estacionalidad; <strong>OLS</strong> para tendencia lineal de incidentes por
            territorio; <strong>Media móvil</strong> para un escenario conservador basado en el tramo reciente;{' '}
            <strong>ARIMA</strong> o <strong>SARIMA</strong> con los mismos mínimos de historia que en la proyección
            mensual.
          </li>
          <li>
            <strong>Patrones día×hora y día de semana:</strong> el modelo define el total a
            repartir; la forma del mapa sale del historial. Use <strong>Estacional</strong> por defecto.
            Si cambia el modelo y la franja líder no se mueve, es habitual: cambia la escala, no el ranking.
          </li>
          <li>
            <strong>Prioridad territorial (P05):</strong> el componente «tendencia» del índice usa <strong>OLS</strong> fijo
            por ahora; la evaluación de modelos para esta sección se hará en una fase posterior.
          </li>
          <li>
            <strong>Señales para cambiar de modelo:</strong> lea el mensaje de <em>interpretación del ajuste</em> bajo
            el gráfico (R² / MAPE); active <strong>Excluir mar–ago 2020</strong> si el confinamiento distorsiona la
            tendencia; amplíe fechas o pruebe estacional si OLS o MA quedan planos o muy alejados de la serie
            observada.
          </li>
          <li>
            <strong>ARIMA y SARIMA — ¿por qué piden más meses?</strong> No es un límite arbitrario del sistema: cada
            modelo debe estimar varios parámetros (autoregresión, media móvil, diferenciación y, en SARIMA, componente
            estacional con periodo 12). Con poca historia esos parámetros quedan inestables y la proyección puede
            seguir el ruido de un mes atípico en lugar de un patrón real.
            <ul>
              <li>
                <strong>ARIMA (mín. 12 meses):</strong> el ajuste usa ARIMA(2,1,3) por defecto; diferenciación consume
                una observación y hay que estimar coeficientes AR y MA con datos suficientes; ~12 puntos es el piso habitual
                en series temporales.
              </li>
              <li>
                <strong>SARIMA (mín. 24 meses):</strong> para distinguir «enero sube porque es enero» de un pico puntual
                hace falta ver <strong>dos ciclos anuales completos</strong> (2 × 12 meses). Con un solo año no se puede
                separar estacionalidad de variación aleatoria.
              </li>
              <li>
                <strong>Proporción de fatales (P07):</strong> además del mínimo del modelo, solo entran al ajuste los meses
                con <strong>≥ 10 víctimas</strong> (el % sería demasiado inestable con menos volumen). Un rango de 18
                meses en el calendario puede dejar solo 14 meses válidos — amplíe fechas o reduzca filtros territoriales
                si el aviso de «serie insuficiente» persiste.
              </li>
            </ul>
          </li>
        </ul>
        <p>
          <strong>Cómo leer la bondad del ajuste</strong>
        </p>
        <BondadMetricasContenido />
        <p>
          Si un bloque queda vacío, amplíe fechas, quite filtros muy restrictivos o pruebe otro modelo. Las
          proyecciones son escenarios orientativos, no predicciones con intervalo de confianza.
        </p>
      </div>
    </details>
  )
}

function precisionDesdeMape(mape) {
  const n = Number(mape)
  if (mape == null || Number.isNaN(n)) return null
  return Math.max(0, Math.min(100, Math.round((100 - n) * 10) / 10))
}

function HoldoutConfiabilidadGuia() {
  return (
    <details className="prioridad-ayuda-details holdout-guia-details">
      <summary>¿Cómo funciona la prueba del modelo?</summary>
      <div className="muted small holdout-guia-body">
        <p>
          Al final del periodo que eligió, el sistema aparta 3 o 6 meses, entrena el modelo <em>sin</em> esos meses y
          calcula qué habría predicho. Luego compara con lo que realmente ocurrió. Es como preguntar: «si no hubiera
          visto estos meses, ¿los habría acertado?»
        </p>
        <p>
          <strong>Ajuste al historial vs prueba:</strong> bajo el gráfico ve si el modelo sigue bien la serie pasada.
          En este panel ve si también acierta en meses recientes que no usó al entrenar. Para decidir qué modelo usar,
          la prueba suele ser más útil que el R² del gráfico.
        </p>
        <p>
          <strong>Rango de fechas:</strong> con pocos meses (menos de un año) muchos modelos no alcanzan a estimar la
          estacionalidad. ARIMA pide al menos unos 12 meses de ajuste; SARIMA, unos 24. Si activó «Excluir mar–ago
          2020», esos meses no entran al cálculo aunque sigan visibles en el gráfico.
        </p>
        <p>
          <strong>Precisión estimada:</strong> se obtiene restando el MAPE de 100 %. Un MAPE de 15 % en la prueba
          equivale a una precisión de unos 85 %. Como referencia, un MAPE de 20 % o menos (precisión de al menos 80 %)
          se considera aceptable para este tipo de proyección mensual.
        </p>
        <p>
          Si el ajuste al historial se ve excelente pero la prueba sale mal, el modelo probablemente se está
          ajustando demasiado al pasado. Pruebe estacional, media móvil o amplíe el rango de fechas.
        </p>
      </div>
    </details>
  )
}

function HoldoutEvaluacionPanel({ meta, unidadPct = false }) {
  const h = meta?.holdout
  if (!h) return null

  const precision = precisionDesdeMape(h.mape_pct)
  const cumple80 = precision != null && precision >= 80
  const fmtVal = (v) =>
    v == null || v === undefined
      ? '—'
      : unidadPct
        ? `${typeof v === 'number' ? v.toLocaleString('es-CO', { maximumFractionDigits: 2 }) : v}%`
        : typeof v === 'number'
          ? v.toLocaleString('es-CO')
          : String(v)

  if (!h.activo) {
    return (
      <>
        <details className="holdout-panel">
          <summary className="small">Prueba del modelo (no disponible)</summary>
          <p className="muted small">{h.motivo || 'No hay datos suficientes para hacer la prueba con meses reservados.'}</p>
        </details>
        <HoldoutConfiabilidadGuia />
      </>
    )
  }

  return (
    <>
      <details className="holdout-panel">
        <summary className="small">
          Prueba del modelo — últimos {h.holdout_meses} meses reservados
        </summary>
        <div className="holdout-panel-body">
          <p className="muted small">{h.metodo}</p>
          <p className="muted small">
            Entrenado hasta <strong>{h.ultimo_mes_entrenamiento}</strong> · comparado con{' '}
            <strong>{h.primer_mes_prueba}</strong> — <strong>{h.ultimo_mes_prueba}</strong>
          </p>
          <p className="muted small holdout-metricas-linea">
            <strong>En la prueba:</strong> R² ≈ <strong>{h.r2}</strong> · RMSE ≈{' '}
            <strong>{h.rmse}</strong>
            {h.mape_pct != null ? (
              <>
                {' '}
                · MAPE ≈ <strong>{h.mape_pct} %</strong>
              </>
            ) : null}
            {precision != null ? (
              <>
                {' '}
                · Precisión estimada ≈ <strong>{precision} %</strong>
              </>
            ) : null}
          </p>
          {precision != null ? (
            <p
              className={`holdout-umbral-badge ${cumple80 ? 'holdout-umbral-badge--ok' : 'holdout-umbral-badge--warn'}`}
              role="status"
            >
              {cumple80 ? (
                <>
                  <strong>Precisión aceptable</strong> en la prueba (error medio del 20 % o menos).
                </>
              ) : (
                <>
                  <strong>Precisión baja</strong> en la prueba. Pruebe otro modelo o amplíe el rango de fechas.
                </>
              )}
            </p>
          ) : null}
          {h.interpretacion_holdout ? (
            <p className={`bondad-interpretacion bondad-${h.bondad_nivel || 'moderado'}`} role="status">
              {h.interpretacion_holdout}
            </p>
          ) : null}
          {h.meses_prueba?.length > 0 ? (
            <div className="prioridad-table-wrap holdout-table-wrap">
              <table className="prioridad-table holdout-table">
                <thead>
                  <tr>
                    <th>Mes</th>
                    <th>Observado</th>
                    <th>Predicho</th>
                    <th>Error abs.</th>
                    <th>Error %</th>
                  </tr>
                </thead>
                <tbody>
                  {h.meses_prueba.map((row) => (
                    <tr key={row.mes_clave}>
                      <td>{row.mes_etiqueta}</td>
                      <td>{fmtVal(row.observados)}</td>
                      <td>{fmtVal(row.predichos)}</td>
                      <td>{fmtVal(row.error_abs)}</td>
                      <td>{row.error_pct != null ? `${row.error_pct} %` : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      </details>
      <HoldoutConfiabilidadGuia />
    </>
  )
}

function BondadInterpretacion({ meta, titulo = 'Interpretación del ajuste' }) {
  const texto = meta?.interpretacion_bondad ?? meta?.coeficientes?.interpretacion_bondad
  const nivel = meta?.bondad_nivel ?? meta?.coeficientes?.bondad_nivel
  if (!texto || meta?.sin_modelo) return null
  return (
    <p className={`bondad-interpretacion bondad-${nivel || 'moderado'}`} role="status">
      <strong>{titulo}:</strong> {texto}
    </p>
  )
}

function ProporcionCoefResumen({ meta }) {
  const c = meta?.coeficientes
  if (!c || meta?.sin_modelo) return null
  const mod = meta.modelo || 'estacional'
  const bondad = metricasBondad(c)
  if (mod === 'logistica') {
    return (
      <>
        Logit-lineal: pendiente en escala logit ≈ <strong>{c.pendiente_logit_mes ?? '—'}</strong>. {bondad}
      </>
    )
  }
  if (mod === 'media_movil') {
    return (
      <>
        Media móvil del % fatales (ventana <strong>{c.ventana_meses ?? meta?.ventana_meses ?? '—'}</strong> meses):
        último valor ≈ <strong>{c.ultima_media_movil ?? '—'}</strong>%. {bondad}
      </>
    )
  }
  if (mod === 'estacional') {
    return (
      <>
        Estacional del % fatales: tendencia ≈ <strong>{c.pendiente_t_mes ?? '—'}</strong> (unidades del
        ajuste). {bondad}
        {c.incluye_efecto_anual ? (
          <>
            {' '}
            Incluye <strong>efecto por año</strong> (ref. {c.referencia_anio}).
          </>
        ) : null}{' '}
        Enero = mes referencia.
      </>
    )
  }
  if (mod === 'logit_offset') {
    return (
      <>
        Logit con exposición (peso = víctimas/mes): tendencia logit ≈{' '}
        <strong>{c.pendiente_t_mes ?? '—'}</strong>. {bondad}
      </>
    )
  }
  if (mod === 'ratio_compuesto') {
    return (
      <>
        Ratio compuesto: estacional sobre fatales y víctimas por separado; % = cociente proyectado.{' '}
        {bondad}
      </>
    )
  }
  if (mod === 'arima' || mod === 'sarima') {
    const orden = c.orden_arima?.join(',') ?? '—'
    const est = c.orden_estacional?.join(',') ?? null
    const etiquetaOrden =
      mod === 'sarima' && est ? `(${orden})×(${est})` : `(${orden})`
    return (
      <>
        {mod === 'sarima' ? 'SARIMA' : 'ARIMA'}
        <strong>{etiquetaOrden}</strong> sobre % fatales · AIC ≈ <strong>{c.aic ?? '—'}</strong>, BIC ≈{' '}
        <strong>{c.bic ?? '—'}</strong>. {bondad}
      </>
    )
  }
  return (
    <>
      OLS del %: pendiente ≈ <strong>{c.pendiente_b_mes ?? '—'}</strong> puntos porcentuales/mes. {bondad}
    </>
  )
}

function PatronesGuiaInterpretacion() {
  return (
    <details className="prioridad-ayuda-details patrones-guia-details">
      <summary>¿Cómo leer los patrones proyectados?</summary>
      <div className="muted small patrones-guia-body">
        <p>
          Este bloque responde <strong>cuándo</strong> del horizonte elegido podrían concentrarse
          más incidentes. Toma el total que proyecta el <strong>bloque 1</strong> (modelo y horizonte
          de proyección mensual, siempre sobre <strong>incidentes</strong>) y lo reparte según cómo se
          distribuyeron en el periodo que filtró arriba.
        </p>
        <p>
          <strong>Matriz día × hora (P12)</strong> — cada celda es una combinación día de la semana
          y hora. Las celdas más oscuras en «Proyección» son las franjas con más carga esperada.
          «Periodo seleccionado» muestra lo que ya ocurrió; «Diferencia» resta periodo de proyección
          celda a celda (no confundir con comparar mes a mes).
        </p>
        <p>
          <strong>Por día de semana (P13)</strong> — resume el mismo total en siete barras. Sirve
          para ver si la semana proyectada sigue cargándose, por ejemplo, en martes o en fin de semana.
        </p>
        <p>
          <strong>Modelo:</strong> no hay selector aquí. Cambie modelo y horizonte en la sección 1; el
          patrón relativo (franja líder, p. ej. martes en la mañana) suele mantenerse porque el reparto
          sigue el historial del periodo filtrado.
        </p>
        <p>
          <strong>Qué sí puede hacer con esto</strong>
        </p>
        <ul>
          <li>Priorizar turnos o controles en las franjas más oscuras del heatmap.</li>
          <li>Comparar si el patrón proyectado se parece al del periodo filtrado.</li>
          <li>Combinar con carga territorial (bloque 3) para tener «dónde» y «cuándo».</li>
        </ul>
        <p>
          <strong>Qué no hace</strong>
        </p>
        <ul>
          <li>No predice un accidente individual ni probabilidad por persona.</li>
          <li>No aprende un modelo aparte por cada celda: extrapola el patrón del periodo.</li>
          <li>Si el aviso dice que no hay modelo mensual, amplíe fechas o quite filtros muy estrechos.</li>
        </ul>
      </div>
    </details>
  )
}

function ProporcionGuiaInterpretacion() {
  return (
    <details className="prioridad-ayuda-details proporcion-guia-details">
      <summary>¿Cómo leer la proporción de fatales?</summary>
      <div className="muted small proporcion-guia-body">
        <p>
          Este bloque no dice cuántos accidentes habrá, sino <strong>qué tan grave fue el mes</strong> en
          términos relativos: de todas las víctimas registradas ese mes, ¿qué porcentaje murió? En Medellín
          ese valor suele ser bajo (menos del 2 %), pero sube o baja según la época del año y los eventos
          puntuales.
        </p>
        <p>
          <strong>Línea azul</strong> — lo que pasó de verdad cada mes.{' '}
          <strong>Línea roja</strong> — lo que el modelo «entiende» del pasado y extrapola unos meses
          adelante. La <strong>zona rosada</strong>, si aparece, es un margen aproximado de error; no es un
          rango oficial de predicción.
        </p>
        <p>
          <strong>Qué modelo elegir</strong>
        </p>
        <ul>
          <li>
            <strong>Estacional sobre %</strong> (recomendado) — si quiere ver qué meses del calendario
            suelen ser más graves, además de una tendencia suave.
          </li>
          <li>
            <strong>Logit con exposición</strong> — cuando el número de víctimas varía mucho de un mes a
            otro; los meses con más víctimas pesan más en el cálculo.
          </li>
          <li>
            <strong>Ratio compuesto</strong> — proyecta por separado cuántas víctimas y cuántas fatales
            podrían haber, y luego calcula el %. Útil si ya confía en la lógica de la proyección mensual.
          </li>
          <li>
            <strong>Media móvil</strong> — lectura conservadora: «como los últimos meses», sin estacionalidad
            elaborada.
          </li>
        </ul>
        <p>
          Los modelos bajo «avanzados» (OLS, logit simple, ARIMA) casi nunca funcionan bien aquí; están
          por comparación, no como recomendación.
        </p>
        <p>
          <strong>Prueba con meses reservados</strong> — despliegue el panel bajo el gráfico. El sistema
          entrena sin los últimos meses y mira si hubiera acertado el %. Si el error en esa prueba supera
          ~20 %, tome la proyección con cautela aunque el gráfico se vea bien ajustado.
        </p>
        <p>
          <strong>Antes de confiar en el resultado</strong>
        </p>
        <ul>
          <li>Deje activado <strong>Excluir mar–ago 2020</strong> salvo que quiera estudiar el confinamiento.</li>
          <li>Prefiera al menos <strong>dos años</strong> de historia (unos 24 meses con datos válidos).</li>
          <li>Si filtra una sola comuna o clase, el % puede saltar mucho mes a mes; use el desglose por comuna solo como exploración.</li>
          <li>Un mes con menos de 10 víctimas no entra al ajuste (el % sería demasiado inestable).</li>
        </ul>
        <p>
          Complemente con el bloque 1 (cuántos fatales en total) y el bloque 2 (prioridad territorial).
          Ninguno de los tres sustituye a los otros.
        </p>
      </div>
    </details>
  )
}

function ProporcionUmbralesR2({ meta }) {
  const u = meta?.umbrales_r2_p07
  if (!u) return null
  return (
    <>
      <p className="muted small proporcion-umbrales-r2">
        <strong>Referencia de R² en este bloque:</strong> bueno {u.bueno}; moderado {u.moderado}; bajo{' '}
        {u.bajo}. En porcentajes tan pequeños es normal quedarse en «moderado»; mire también la prueba con
        meses reservados.
      </p>
      <BondadMetricasGuia meta={meta} />
    </>
  )
}

function ProporcionBondadVisible({ meta }) {
  const c = meta?.coeficientes
  if (!c || meta?.sin_modelo) return null
  const bondad = metricasBondad(c)
  if (!bondad) return null
  const nivel = meta?.bondad_nivel ?? c?.bondad_nivel
  return (
    <p className={`proporcion-bondad-resumen bondad-${nivel || 'moderado'}`}>
      <strong>Bondad del ajuste:</strong> {bondad}
      {c.nota ? <span className="muted"> — {c.nota}</span> : null}
    </p>
  )
}

function CoefResumen({ meta }) {
  const c = meta?.coeficientes
  if (!c || meta?.sin_modelo) return null
  const mod = meta.modelo || 'ols'
  const bondad = metricasBondad(c)
  if (mod === 'ols') {
    return (
      <>
        Ajuste en el rango: pendiente mensual ≈ <strong>{c.pendiente_b_mes ?? '—'}</strong>. {bondad}
        <span className="muted"> (En series con estacionalidad y shocks, R² moderado es habitual.)</span>
      </>
    )
  }
  if (mod === 'estacional') {
    return (
      <>
        Ajuste estacional: tendencia ≈ <strong>{c.pendiente_t_mes ?? '—'}</strong>. {bondad}
        {c.incluye_efecto_anual ? (
          <> Incluye <strong>efecto por año</strong> (ref. {c.referencia_anio}).</>
        ) : null}{' '}
        Enero = referencia de mes.
      </>
    )
  }
  if (mod === 'media_movil') {
    return (
      <>
        Media móvil (ventana <strong>{c.ventana_meses ?? meta?.ventana_meses ?? '—'}</strong> meses): último
        valor ≈ <strong>{c.ultima_media_movil ?? '—'}</strong>. {bondad}
        <span className="muted"> (Suaviza la serie; la proyección repite el nivel reciente.)</span>
      </>
    )
  }
  if (mod === 'arima' || mod === 'sarima') {
    const orden = c.orden_arima?.join(',') ?? '—'
    const est = c.orden_estacional?.join(',') ?? null
    const etiquetaOrden =
      mod === 'sarima' && est ? `(${orden})×(${est})` : `(${orden})`
    return (
      <>
        {mod === 'sarima' ? 'SARIMA' : 'ARIMA'}
        <strong>{etiquetaOrden}</strong> · AIC ≈ <strong>{c.aic ?? '—'}</strong>, BIC ≈{' '}
        <strong>{c.bic ?? '—'}</strong>. {bondad}
        {c.nota ? <span className="muted"> {c.nota}</span> : null}
      </>
    )
  }
  if (c.fallback_estacional) {
    return (
      <>
        Ajuste estacional (respaldo): tendencia ≈ <strong>{c.pendiente_t_mes ?? '—'}</strong>, R² ≈{' '}
        <strong>{c.r2_pseudo ?? c.r2 ?? '—'}</strong>. {c.nota}
      </>
    )
  }
  return (
    <>
      Poisson: factor mensual ≈ <strong>{c.factor_tendencia_mensual ?? '—'}</strong>
      {c.cambio_tendencia_pct_aprox != null ? (
        <>
          {' '}
          ({c.cambio_tendencia_pct_aprox > 0 ? '+' : ''}
          {c.cambio_tendencia_pct_aprox}% aprox. por mes)
        </>
      ) : null}
      . {metricasBondad(c)} {c.nota}
    </>
  )
}

function formatDateEs(iso) {
  if (!iso) return ''
  const [y, m, day] = iso.split('-').map(Number)
  const d = new Date(y, m - 1, day)
  return d.toLocaleDateString('es-CO', { day: 'numeric', month: 'short', year: 'numeric' })
}

function useMediaQuery(query) {
  return useSyncExternalStore(
    (onStoreChange) => {
      if (typeof window === 'undefined') return () => {}
      const mq = window.matchMedia(query)
      mq.addEventListener('change', onStoreChange)
      return () => mq.removeEventListener('change', onStoreChange)
    },
    () => (typeof window !== 'undefined' ? window.matchMedia(query).matches : false),
    () => false,
  )
}

export function Predicciones() {
  const [catalogos, setCatalogos] = useState({ comunas: [], clases_incidente: [] })
  const [barrios, setBarrios] = useState([])
  const [rangoMeta, setRangoMeta] = useState(null)

  const [desde, setDesde] = useState(FECHAS_REF_MEDE.default_desde)
  const [hasta, setHasta] = useState(FECHAS_REF_MEDE.default_hasta)
  const [comunaId, setComunaId] = useState('')
  const [barrioId, setBarrioId] = useState('')
  const [claseId, setClaseId] = useState('')
  const [modoTerritorio, setModoTerritorio] = useState('registro')

  const [predicciones, setPredicciones] = useState(null)
  const [horizontePred, setHorizontePred] = useState(3)
  const [holdoutMeses, setHoldoutMeses] = useState(3)
  const [horizonteProp, setHorizonteProp] = useState(3)
  const [horizonteCarga, setHorizonteCarga] = useState(3)
  const [modeloPred, setModeloPred] = useState('ols')
  const [ventanaMaPred, setVentanaMaPred] = useState(3)
  const [arimaOrderPred, setArimaOrderPred] = useState(ARIMA_ORDER_DEFAULT)
  const [sarimaSeasonalPred, setSarimaSeasonalPred] = useState(SARIMA_SEASONAL_DEFAULT)
  const [variablePred, setVariablePred] = useState('incidentes')
  const [desglosePorClase, setDesglosePorClase] = useState(false)
  const [excluirCovid, setExcluirCovid] = useState(true)
  const [serieClaseIdx, setSerieClaseIdx] = useState(0)
  const [nivelPrioridad, setNivelPrioridad] = useState('comuna')
  const [ordenPrioridad, setOrdenPrioridad] = useState('compuesto')
  const [prioridad, setPrioridad] = useState(null)
  const [modeloProp, setModeloProp] = useState('estacional')
  const [ventanaMaProp, setVentanaMaProp] = useState(3)
  const [holdoutMesesProp, setHoldoutMesesProp] = useState(3)
  const [modelosAvanzadosProp, setModelosAvanzadosProp] = useState(false)
  const [arimaOrderProp, setArimaOrderProp] = useState(ARIMA_ORDER_DEFAULT)
  const [sarimaSeasonalProp, setSarimaSeasonalProp] = useState(SARIMA_SEASONAL_DEFAULT)
  const [desgloseComunaProp, setDesgloseComunaProp] = useState(false)
  const [serieComunaIdx, setSerieComunaIdx] = useState(0)
  const [proporcion, setProporcion] = useState(null)
  const [nivelCarga, setNivelCarga] = useState('comuna')
  const [modeloCarga, setModeloCarga] = useState('estacional')
  const [ventanaMaCarga, setVentanaMaCarga] = useState(3)
  const [arimaOrderCarga, setArimaOrderCarga] = useState(ARIMA_ORDER_DEFAULT)
  const [sarimaSeasonalCarga, setSarimaSeasonalCarga] = useState(SARIMA_SEASONAL_DEFAULT)
  const [cargaEsperada, setCargaEsperada] = useState(null)
  const [matrizProyectada, setMatrizProyectada] = useState(null)
  const [diaSemanaProyectado, setDiaSemanaProyectado] = useState(null)
  const [loadingProyeccion, setLoadingProyeccion] = useState(false)
  const [loadingProporcion, setLoadingProporcion] = useState(false)
  const [loadingCarga, setLoadingCarga] = useState(false)
  const [loadingPatrones, setLoadingPatrones] = useState(false)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
  const skipProyeccionAutoRef = useRef(true)
  const skipProporcionAutoRef = useRef(true)
  const skipCargaAutoRef = useRef(true)
  const skipPatronesAutoRef = useRef(true)

  const chartLayoutCompact = useMediaQuery(`(max-width: ${CHART_COMPACT_MAX_PX}px)`)

  const prediccionesChartHeight = chartLayoutCompact ? 280 : 340
  const yAxisTickWidth = chartLayoutCompact ? 34 : 48

  const legendTopPropsResolved = useMemo(
    () =>
      chartLayoutCompact
        ? {
            ...LEGEND_TOP_PROPS,
            wrapperStyle: { ...LEGEND_TOP_PROPS.wrapperStyle, fontSize: '10px', lineHeight: '14px' },
          }
        : LEGEND_TOP_PROPS,
    [chartLayoutCompact],
  )

  const selMin = rangoMeta?.selector_fecha_min ?? FECHAS_REF_MEDE.selector_fecha_min
  const selMax = rangoMeta?.selector_fecha_max ?? FECHAS_REF_MEDE.selector_fecha_max

  const filtrosQuery = useCallback(
    () => ({
      desde,
      hasta,
      comuna_id: comunaId || undefined,
      barrio_id: barrioId || undefined,
      clase_incidente_id: claseId || undefined,
      ...(modoTerritorio === 'espacial' ? { territorio: 'espacial' } : {}),
    }),
    [desde, hasta, comunaId, barrioId, claseId, modoTerritorio],
  )

  const prediccionesQuery = useCallback(
    () => ({
      ...filtrosQuery(),
      horizonte_meses: horizontePred,
      holdout_meses: holdoutMeses,
      modelo: modeloPred,
      variable: variablePred,
      ...(ventanaMaQuery(modeloPred, ventanaMaPred)),
      ...arimaParamsQuery(modeloPred, arimaOrderPred, sarimaSeasonalPred),
      ...(desglosePorClase && !claseId ? { desglose_clase: '1' } : {}),
      ...(excluirCovid ? { excluir_covid: '1' } : {}),
    }),
    [
      filtrosQuery,
      horizontePred,
      holdoutMeses,
      modeloPred,
      ventanaMaPred,
      arimaOrderPred,
      sarimaSeasonalPred,
      variablePred,
      desglosePorClase,
      claseId,
      excluirCovid,
    ],
  )

  const bloqueGrafico = useMemo(() => {
    if (!predicciones) return null
    if (predicciones.meta?.desglose_clase && predicciones.series_por_clase?.length) {
      return predicciones.series_por_clase[serieClaseIdx] ?? predicciones.series_por_clase[0]
    }
    return predicciones
  }, [predicciones, serieClaseIdx])

  const metaActiva = bloqueGrafico?.meta ?? predicciones?.meta

  const prediccionesLineData = useMemo(() => {
    if (!bloqueGrafico?.serie_historica?.length) return []
    return buildPrediccionesLineData(bloqueGrafico.serie_historica, bloqueGrafico.proyeccion)
  }, [bloqueGrafico])

  const tieneSerie = Boolean(
    predicciones?.serie_historica?.length || predicciones?.series_por_clase?.length,
  )

  const prioridadQuery = useCallback(
    () => ({
      ...filtrosQuery(),
      nivel: nivelPrioridad,
      limite: 15,
      ...(excluirCovid ? { excluir_covid: '1' } : {}),
    }),
    [filtrosQuery, nivelPrioridad, excluirCovid],
  )

  const opcionesModeloProp = useMemo(
    () => (modelosAvanzadosProp ? MODELO_PROP_OPTS : MODELO_PROP_PRINCIPAL),
    [modelosAvanzadosProp],
  )

  useEffect(() => {
    if (!modelosAvanzadosProp && MODELO_PROP_AVANZADO.some((o) => o.value === modeloProp)) {
      setModeloProp('estacional')
    }
  }, [modelosAvanzadosProp, modeloProp])

  const proporcionQuery = useCallback(
    () => ({
      ...filtrosQuery(),
      horizonte_meses: horizonteProp,
      holdout_meses: holdoutMesesProp,
      modelo: modeloProp,
      ...(ventanaMaQuery(modeloProp, ventanaMaProp)),
      ...arimaParamsQuery(modeloProp, arimaOrderProp, sarimaSeasonalProp),
      ...(desgloseComunaProp && !comunaId ? { desglose_comuna: '1' } : {}),
      ...(excluirCovid ? { excluir_covid: '1' } : {}),
    }),
    [
      filtrosQuery,
      horizonteProp,
      holdoutMesesProp,
      modeloProp,
      ventanaMaProp,
      arimaOrderProp,
      sarimaSeasonalProp,
      desgloseComunaProp,
      comunaId,
      excluirCovid,
    ],
  )

  const cargaQuery = useCallback(
    () => ({
      ...filtrosQuery(),
      nivel: nivelCarga,
      limite: 12,
      horizonte_meses: horizonteCarga,
      modelo: modeloCarga,
      ...(ventanaMaQuery(modeloCarga, ventanaMaCarga)),
      ...arimaParamsQuery(modeloCarga, arimaOrderCarga, sarimaSeasonalCarga),
      ...(excluirCovid ? { excluir_covid: '1' } : {}),
    }),
    [filtrosQuery, nivelCarga, horizonteCarga, modeloCarga, ventanaMaCarga, arimaOrderCarga, sarimaSeasonalCarga, excluirCovid],
  )

  const cargaComparativaData = useMemo(
    () => buildCargaComparativaData(cargaEsperada?.ranking, nivelCarga),
    [cargaEsperada, nivelCarga],
  )

  const cargaBarHeight = useMemo(() => {
    const n = Math.max(cargaComparativaData.length, 1)
    const rowH = chartLayoutCompact ? 32 : 36
    const base = chartLayoutCompact ? 72 : 96
    return Math.max(chartLayoutCompact ? 220 : 300, n * rowH + base)
  }, [cargaComparativaData.length, chartLayoutCompact])

  const bloqueProporcion = useMemo(() => {
    if (!proporcion) return null
    if (proporcion.meta?.desglose_comuna && proporcion.series_por_comuna?.length) {
      return proporcion.series_por_comuna[serieComunaIdx] ?? proporcion.series_por_comuna[0]
    }
    return proporcion
  }, [proporcion, serieComunaIdx])

  const proporcionLineData = useMemo(() => {
    if (!bloqueProporcion?.serie_historica?.length) return []
    return buildProporcionLineData(
      bloqueProporcion.serie_historica,
      bloqueProporcion.proyeccion,
    )
  }, [bloqueProporcion])

  const metaProporcion = bloqueProporcion?.meta ?? proporcion?.meta

  const loadProyeccionMensual = useCallback(async () => {
    setLoadingProyeccion(true)
    try {
      const r = await fetchDashboardPrediccionesMensuales(prediccionesQuery())
      setPredicciones(r)
      setSerieClaseIdx(0)
    } catch (e) {
      setPredicciones(null)
      setErr(e instanceof Error ? e.message : 'Error al cargar proyección mensual')
    } finally {
      setLoadingProyeccion(false)
    }
  }, [prediccionesQuery])

  useEffect(() => {
    if (skipProyeccionAutoRef.current) {
      skipProyeccionAutoRef.current = false
      return
    }
    if (!predicciones) return
    void loadProyeccionMensual()
  }, [modeloPred, ventanaMaPred, arimaOrderPred, sarimaSeasonalPred, desglosePorClase, horizontePred, holdoutMeses, loadProyeccionMensual])

  const loadProporcion = useCallback(async () => {
    setLoadingProporcion(true)
    try {
      const prop = await fetchDashboardProporcionFatalesMensual(proporcionQuery())
      setProporcion(prop)
      setSerieComunaIdx(0)
    } catch (e) {
      setProporcion(null)
      setErr(e instanceof Error ? e.message : 'Error al cargar proporción de fatales')
    } finally {
      setLoadingProporcion(false)
    }
  }, [proporcionQuery])

  useEffect(() => {
    if (skipProporcionAutoRef.current) {
      skipProporcionAutoRef.current = false
      return
    }
    if (!proporcion) return
    void loadProporcion()
  }, [modeloProp, ventanaMaProp, arimaOrderProp, sarimaSeasonalProp, desgloseComunaProp, horizonteProp, holdoutMesesProp, loadProporcion])

  const loadCarga = useCallback(async () => {
    setLoadingCarga(true)
    try {
      const carga = await fetchDashboardCargaEsperadaTerritorial(cargaQuery())
      setCargaEsperada(carga)
    } catch (e) {
      setCargaEsperada(null)
      setErr(e instanceof Error ? e.message : 'Error al cargar carga esperada')
    } finally {
      setLoadingCarga(false)
    }
  }, [cargaQuery])

  useEffect(() => {
    if (skipCargaAutoRef.current) {
      skipCargaAutoRef.current = false
      return
    }
    if (!cargaEsperada) return
    void loadCarga()
  }, [nivelCarga, modeloCarga, ventanaMaCarga, arimaOrderCarga, sarimaSeasonalCarga, horizonteCarga, loadCarga])

  const patronesQuery = useCallback(
    () => ({
      ...filtrosQuery(),
      horizonte_meses: horizontePred,
      modelo: modeloPred,
      ...(ventanaMaQuery(modeloPred, ventanaMaPred)),
      ...arimaParamsQuery(modeloPred, arimaOrderPred, sarimaSeasonalPred),
      ...(excluirCovid ? { excluir_covid: '1' } : {}),
    }),
    [
      filtrosQuery,
      horizontePred,
      modeloPred,
      ventanaMaPred,
      arimaOrderPred,
      sarimaSeasonalPred,
      excluirCovid,
    ],
  )

  const loadPatrones = useCallback(async () => {
    setLoadingPatrones(true)
    try {
      const q = patronesQuery()
      const [matrizP, diaP] = await Promise.all([
        fetchDashboardMatrizDiaHoraProyectada(q),
        fetchDashboardPorDiaSemanaProyectado(q),
      ])
      setMatrizProyectada(matrizP)
      setDiaSemanaProyectado(diaP)
    } catch (e) {
      setMatrizProyectada(null)
      setDiaSemanaProyectado(null)
      setErr(e instanceof Error ? e.message : 'Error al cargar patrones proyectados')
    } finally {
      setLoadingPatrones(false)
    }
  }, [patronesQuery])

  useEffect(() => {
    if (skipPatronesAutoRef.current) {
      skipPatronesAutoRef.current = false
      return
    }
    if (!predicciones) return
    void loadPatrones()
  }, [horizontePred, modeloPred, ventanaMaPred, arimaOrderPred, sarimaSeasonalPred, loadPatrones, predicciones])

  const filtrosReporte = useMemo(() => {
    const comuna = (catalogos.comunas || []).find((c) => String(c.id) === comunaId)
    const barrio = barrios.find((b) => String(b.id) === barrioId)
    const clase = (catalogos.clases_incidente || []).find((c) => String(c.id) === claseId)
    const modeloLabel = (opts, value) => opts.find((o) => o.value === value)?.label ?? value
    return {
      desde,
      hasta,
      ...(comuna ? { comuna: comuna.nombre } : {}),
      ...(barrio ? { barrio: barrio.nombre } : {}),
      ...(clase ? { clase_incidente: clase.nombre } : {}),
      territorio: modoTerritorio === 'espacial' ? 'Polígono PostGIS' : 'Registro Mede',
      horizonte_proyeccion: horizontePred,
      horizonte_proporcion: horizonteProp,
      horizonte_carga: horizonteCarga,
      horizonte_patrones: horizontePred,
      modelo_proyeccion: modeloLabel(MODELO_OPTS, modeloPred),
      variable: modeloLabel(VARIABLE_OPTS, variablePred),
      modelo_proporcion: modeloLabel(MODELO_PROP_OPTS, modeloProp),
      modelo_carga: modeloLabel(MODELO_CARGA_OPTS, modeloCarga),
      modelo_patrones: `${modeloLabel(MODELO_OPTS, modeloPred)} (igual que proyección mensual)`,
      nivel_prioridad: nivelPrioridad === 'barrio' ? 'Barrio' : 'Comuna',
      nivel_carga: nivelCarga === 'barrio' ? 'Barrio' : 'Comuna',
      excluir_covid: excluirCovid ? 'Sí' : 'No',
      ...(desglosePorClase && !claseId ? { desglose_clase: 'Sí' } : {}),
      ...(desgloseComunaProp && !comunaId ? { desglose_comuna: 'Sí' } : {}),
      ...(modeloPred === 'media_movil' ? { ventana_ma_proyeccion: `${ventanaMaPred} meses` } : {}),
      ...(modeloProp === 'media_movil' ? { ventana_ma_proporcion: `${ventanaMaProp} meses` } : {}),
      ...(modeloCarga === 'media_movil' ? { ventana_ma_carga: `${ventanaMaCarga} meses` } : {}),
    }
  }, [
    desde,
    hasta,
    comunaId,
    barrioId,
    claseId,
    modoTerritorio,
    catalogos,
    barrios,
    horizontePred,
    horizonteProp,
    horizonteCarga,
    modeloPred,
    variablePred,
    modeloProp,
    modeloCarga,
    nivelPrioridad,
    nivelCarga,
    excluirCovid,
    desglosePorClase,
    desgloseComunaProp,
    ventanaMaPred,
    ventanaMaProp,
    ventanaMaCarga,
  ])

  const queryReporte = useMemo(() => {
    return {
      desde,
      hasta,
      ...(comunaId ? { comuna_id: comunaId } : {}),
      ...(barrioId ? { barrio_id: barrioId } : {}),
      ...(claseId ? { clase_incidente_id: claseId } : {}),
      ...(modoTerritorio === 'espacial' ? { territorio: 'espacial' } : {}),
      horizonte_meses: horizontePred,
      horizonte_prop: horizonteProp,
      horizonte_carga: horizonteCarga,
      horizonte_patrones: horizontePred,
      modelo_pred: modeloPred,
      modelo_prop: modeloProp,
      modelo_carga: modeloCarga,
      modelo_patrones: modeloPred,
      variable: variablePred,
      ...(modeloPred === 'media_movil' ? { ventana_ma_pred: ventanaMaPred } : {}),
      ...(modeloProp === 'media_movil' ? { ventana_ma_prop: ventanaMaProp } : {}),
      ...(modeloCarga === 'media_movil' ? { ventana_ma_carga: ventanaMaCarga } : {}),
      nivel_prioridad: nivelPrioridad,
      nivel_carga: nivelCarga,
      limite_prioridad: 15,
      limite_carga: 12,
      excluir_covid: excluirCovid ? '1' : '0',
      ...(desglosePorClase && !claseId ? { desglose_clase: '1' } : {}),
      ...(desgloseComunaProp && !comunaId ? { desglose_comuna: '1' } : {}),
      serie_clase_idx: serieClaseIdx,
      serie_comuna_idx: serieComunaIdx,
    }
  }, [
    desde,
    hasta,
    comunaId,
    barrioId,
    claseId,
    modoTerritorio,
    horizontePred,
    horizonteProp,
    horizonteCarga,
    modeloPred,
    modeloProp,
    modeloCarga,
    variablePred,
    ventanaMaPred,
    ventanaMaProp,
    ventanaMaCarga,
    nivelPrioridad,
    nivelCarga,
    excluirCovid,
    desglosePorClase,
    desgloseComunaProp,
    serieClaseIdx,
    serieComunaIdx,
  ])

  const applyPrediccionesBundle = useCallback((bundle) => {
    setPredicciones(bundle.predicciones)
    setPrioridad(bundle.prioridad)
    setProporcion(bundle.proporcion)
    setCargaEsperada(bundle.cargaEsperada)
    setMatrizProyectada(bundle.matrizProyectada)
    setDiaSemanaProyectado(bundle.diaSemanaProyectado)
    if (bundle.errors.length > 0) {
      setErr(`Algunos bloques no cargaron: ${bundle.errors.join(' · ')}`)
    }
  }, [])

  const loadPrioridadSolo = useCallback(async () => {
    try {
      const data = await fetchDashboardPrioridadTerritorial(prioridadQuery())
      setPrioridad(data)
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'Error al cargar prioridad territorial')
    }
  }, [prioridadQuery])

  const loadPredicciones = useCallback(async () => {
    setLoading(true)
    setErr(null)
    try {
      const bundle = await fetchPrediccionesBundle({
        prediccionesQuery,
        prioridadQuery,
        proporcionQuery,
        cargaQuery,
        patronesQuery,
      })
      applyPrediccionesBundle(bundle)
      if (!bundle.predicciones && bundle.errors.length > 0) {
        setErr(bundle.errors.join(' · '))
      }
    } catch (e) {
      setPredicciones(null)
      setPrioridad(null)
      setProporcion(null)
      setCargaEsperada(null)
      setMatrizProyectada(null)
      setDiaSemanaProyectado(null)
      setErr(e instanceof Error ? e.message : 'Error al cargar predicciones')
    } finally {
      setLoading(false)
    }
  }, [
    prediccionesQuery,
    prioridadQuery,
    proporcionQuery,
    cargaQuery,
    patronesQuery,
    applyPrediccionesBundle,
  ])

  useEffect(() => {
    void fetchDashboardCatalogos()
      .then(setCatalogos)
      .catch(() => setCatalogos({ comunas: [], clases_incidente: [] }))
  }, [])

  const nivelPrioridadMounted = useRef(false)
  useEffect(() => {
    if (!nivelPrioridadMounted.current) {
      nivelPrioridadMounted.current = true
      return
    }
    void loadPrioridadSolo()
  }, [nivelPrioridad, loadPrioridadSolo])

  const prioridadNivelDatos = prioridad?.meta?.nivel ?? nivelPrioridad
  const prioridadFilas = useMemo(
    () => filasPrioridadTabla(prioridad, ordenPrioridad),
    [prioridad, ordenPrioridad],
  )
  const mostrarColVol = ordenPrioridad === 'compuesto'

  useEffect(() => {
    if (!comunaId) {
      setBarrios([])
      return
    }
    void fetchDashboardBarrios(comunaId)
      .then((r) => setBarrios(r.barrios || []))
      .catch(() => setBarrios([]))
  }, [comunaId])

  useEffect(() => {
    let alive = true
    ;(async () => {
      setLoading(true)
      setErr(null)
      try {
        let rango
        try {
          rango = await fetchDashboardRangoFechas()
        } catch {
          rango = {
            ...FECHAS_REF_MEDE,
            hay_datos: false,
            referencia_fuente:
              'No se pudo leer el rango desde el servidor; usando fechas del archivo Mede depurado (aprox. 2014–2021).',
          }
        }
        if (!alive) return
        setRangoMeta(rango)
        setDesde(rango.default_desde)
        setHasta(rango.default_hasta)

        const base = {
          desde: rango.default_desde,
          hasta: rango.default_hasta,
          horizonte_meses: 3,
          excluir_covid: '1',
        }
        const patronBase = {
          ...base,
          horizonte_meses: 3,
          modelo: 'ols',
          excluir_covid: '1',
        }
        const bundle = await fetchPrediccionesBundle({
          prediccionesQuery: () => ({ ...base, modelo: 'ols' }),
          prioridadQuery: () => ({ ...base, nivel: 'comuna', limite: 15, excluir_covid: '1' }),
          proporcionQuery: () => ({ ...base, modelo: 'estacional' }),
          cargaQuery: () => ({
            ...base,
            nivel: 'comuna',
            limite: 12,
            modelo: 'estacional',
            horizonte_meses: 3,
          }),
          patronesQuery: () => patronBase,
        })
        if (!alive) return
        setPredicciones(bundle.predicciones)
        setPrioridad(bundle.prioridad)
        setProporcion(bundle.proporcion)
        setCargaEsperada(bundle.cargaEsperada)
        setMatrizProyectada(bundle.matrizProyectada)
        setDiaSemanaProyectado(bundle.diaSemanaProyectado)
        if (bundle.errors.length > 0) {
          setErr(`Algunos bloques no cargaron: ${bundle.errors.join(' · ')}`)
        }
      } catch (e) {
        if (!alive) return
        setPredicciones(null)
        setErr(e instanceof Error ? e.message : 'Error al cargar predicciones')
      } finally {
        if (alive) setLoading(false)
      }
    })()
    return () => {
      alive = false
    }
  }, [])

  return (
    <div className="dashboard predicciones-page">
      <header className="page-intro page-intro-with-actions">
        <div className="page-intro-text">
          <h1>Predicciones</h1>
          <p className="muted">
            Proyecciones descriptivas por bloques independientes: cada sección permite elegir el modelo que mejor se
            ajuste al periodo y a la naturaleza de los datos. Los filtros superiores (fechas, territorio, variable y
            COVID) aplican a todas las secciones.
          </p>
          <PrediccionesFiltrosGuia />
        </div>
        <div className="page-intro-actions">
          <GenerarReporteButton
            seccion="predicciones"
            seccionEtiqueta="Predicciones"
            filtros={filtrosReporte}
            query={queryReporte}
          />
        </div>
      </header>

      {loading && !predicciones && !err && <p className="muted">Cargando rango de fechas y serie…</p>}

      <section className="panel filter-panel filter-panel-shared">
        <h2>Filtros compartidos del periodo</h2>
        <p className="muted small filter-help">
          Aplican a todas las secciones: fechas, territorio, variable y exclusión COVID. El <strong>modelo</strong> se
          elige dentro de cada bloque de predicción.
        </p>
        {rangoMeta?.referencia_fuente && (
          <p className="muted small filter-help" style={{ color: '#9a3412' }}>
            {rangoMeta.referencia_fuente}
          </p>
        )}
        <div className="filter-grid">
          <label className="filter-field">
            Desde
            <input
              type="date"
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
              min={selMin}
              max={hasta}
            />
          </label>
          <label className="filter-field">
            Hasta
            <input
              type="date"
              value={hasta}
              onChange={(e) => setHasta(e.target.value)}
              min={desde}
              max={selMax}
            />
          </label>
          <label className="filter-field">
            Comuna
            <select
              value={comunaId}
              onChange={(e) => {
                setComunaId(e.target.value)
                setBarrioId('')
              }}
            >
              <option value="">Todas</option>
              {(catalogos.comunas || []).map((c) => (
                <option key={c.id} value={String(c.id)}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            Barrio
            <select
              value={barrioId}
              onChange={(e) => setBarrioId(e.target.value)}
              disabled={!comunaId}
            >
              <option value="">Todos</option>
              {barrios.map((b) => (
                <option key={b.id} value={String(b.id)}>
                  {b.nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            Clase de incidente
            <select
              value={claseId}
              onChange={(e) => {
                setClaseId(e.target.value)
                if (e.target.value) setDesglosePorClase(false)
              }}
            >
              <option value="">Todas</option>
              {(catalogos.clases_incidente || []).map((c) => (
                <option key={c.id} value={String(c.id)}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            Territorio (filtros)
            <select value={modoTerritorio} onChange={(e) => setModoTerritorio(e.target.value)}>
              <option value="registro">Registro Mede (default)</option>
              <option value="espacial">Polígono PostGIS</option>
            </select>
          </label>
          <label className="filter-field">
            Variable
            <select value={variablePred} onChange={(e) => setVariablePred(e.target.value)}>
              {VARIABLE_OPTS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field filter-field-checkbox">
            <input
              type="checkbox"
              checked={excluirCovid}
              onChange={(e) => setExcluirCovid(e.target.checked)}
            />
            Excluir mar–ago 2020 del ajuste (confinamiento COVID)
          </label>
          <div className="filter-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => void loadPredicciones()}
              disabled={loading}
            >
              {loading ? 'Actualizando…' : 'Actualizar'}
            </button>
          </div>
        </div>
      </section>

      {err && <p className="form-error">{err}</p>}

      {!loading && predicciones && !tieneSerie && (
        <p className="muted panel">No hay serie mensual para estos filtros. Amplíe el rango de fechas.</p>
      )}

      {tieneSerie && metaActiva && (
        <section className="panel chart-panel-comparativo predicciones-seccion">
          <h2>
            1. Proyección mensual — {metaActiva.variable_etiqueta || 'serie mensual'}
            {predicciones.meta?.desglose_clase ? ' (por clase)' : ''}
            {loadingProyeccion && <span className="muted small"> — actualizando…</span>}
          </h2>
          <p className="muted small">
            Evalúe aquí el modelo que mejor ajuste la serie mensual de la variable seleccionada en los filtros
            compartidos.
          </p>
          <SeccionModeloToolbar
            modelo={modeloPred}
            onModeloChange={setModeloPred}
            opciones={MODELO_OPTS}
            ventanaMa={ventanaMaPred}
            onVentanaMaChange={setVentanaMaPred}
            horizonte={horizontePred}
            onHorizonteChange={setHorizontePred}
            loading={loadingProyeccion}
            horizonteId="horizonte-proyeccion-mensual"
            arimaOrder={arimaOrderPred}
            onArimaOrderChange={setArimaOrderPred}
            sarimaSeasonal={sarimaSeasonalPred}
            onSarimaSeasonalChange={setSarimaSeasonalPred}
          >
            <label className="checkbox-inline filter-field-checkbox">
              <input
                type="checkbox"
                checked={desglosePorClase}
                disabled={Boolean(claseId) || loadingProyeccion}
                onChange={(e) => {
                  setDesglosePorClase(e.target.checked)
                  setSerieClaseIdx(0)
                }}
              />
              Desglose por clase (hasta 15)
            </label>
            <label>
              Meses de prueba
              <select
                className="predicciones-select"
                value={holdoutMeses}
                disabled={loadingProyeccion}
                onChange={(e) => setHoldoutMeses(Number(e.target.value))}
              >
                {HOLDOUT_MESES_OPTS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
          </SeccionModeloToolbar>
          <p className="muted small seccion-modelo-hint">
            Cambios de <strong>modelo</strong>, <strong>ventana</strong> u <strong>horizonte</strong> recalculan solo
            esta sección. Fechas y filtros compartidos requieren <strong>Actualizar</strong>.
          </p>
          <p className="muted small">
            <strong>Periodo de ajuste:</strong> {formatDateEs(metaActiva.fecha_inicio)} —{' '}
            {formatDateEs(metaActiva.fecha_fin)}. <strong>Modelo:</strong>{' '}
            {MODELO_OPTS.find((o) => o.value === metaActiva.modelo)?.label ?? metaActiva.modelo}.{' '}
            {metaActiva.metodo || predicciones.meta?.limitaciones}
          </p>
          <p className="muted small">{metaActiva.limitaciones || predicciones.meta?.limitaciones}</p>
          {predicciones.meta?.desglose_clase && predicciones.series_por_clase?.length > 0 && (
            <label className="filter-field" style={{ maxWidth: 420, marginBottom: 8 }}>
              Clase a visualizar
              <select
                value={String(serieClaseIdx)}
                onChange={(e) => setSerieClaseIdx(Number(e.target.value) || 0)}
              >
                {predicciones.series_por_clase.map((s, i) => (
                  <option key={s.clase_incidente_id} value={String(i)}>
                    {s.clase_nombre}
                  </option>
                ))}
              </select>
            </label>
          )}
          {metaActiva.sin_modelo ? (
            <p className="muted small" role="status">
              Hay menos de <strong>{minMesesModelo(metaActiva.modelo, metaActiva.ventana_meses)} meses</strong> con datos en el rango; no se
              calcula proyección. Amplíe las fechas o verifique datos.
            </p>
          ) : (
            <>
              <p className="muted small">
                <CoefResumen meta={metaActiva} />
              </p>
              <BondadInterpretacion meta={metaActiva} />
              <BondadConsejoModelo meta={metaActiva} />
              <BondadMetricasGuia incluirHoldout />
              <HoldoutEvaluacionPanel meta={metaActiva} />
            </>
          )}
          <div className="chart-box chart-box-tall">
            <ResponsiveContainer width="100%" height={prediccionesChartHeight}>
              <LineChart
                data={prediccionesLineData}
                margin={{
                  top: chartLayoutCompact ? 40 : 48,
                  right: chartLayoutCompact ? 6 : 16,
                  left: chartLayoutCompact ? 4 : 12,
                  bottom: chartLayoutCompact ? 36 : 44,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis
                  dataKey="mes"
                  tick={{ fontSize: chartLayoutCompact ? 9 : 11 }}
                  angle={prediccionesLineData.length > 10 ? -28 : 0}
                  textAnchor={prediccionesLineData.length > 10 ? 'end' : 'middle'}
                  height={prediccionesLineData.length > 10 ? 52 : 36}
                  interval={0}
                  label={{
                    value: 'Mes',
                    position: 'bottom',
                    offset: chartLayoutCompact ? 20 : 16,
                    fontSize: chartLayoutCompact ? 11 : 12,
                    fill: '#64748b',
                  }}
                />
                <YAxis
                  allowDecimals={false}
                  tick={{ fontSize: chartLayoutCompact ? 9 : 11 }}
                  width={yAxisTickWidth}
                  label={{
                    value: `${metaActiva.variable_etiqueta || 'Conteo'} (mensual)`,
                    angle: -90,
                    position: 'left',
                    offset: chartLayoutCompact ? 6 : 10,
                    style: {
                      textAnchor: 'middle',
                      fontSize: chartLayoutCompact ? 10 : 12,
                      fill: '#64748b',
                    },
                  }}
                />
                <Tooltip
                  formatter={(val, name) => [
                    val != null ? Number(val).toLocaleString('es-CO') : '—',
                    name,
                  ]}
                />
                <Legend {...legendTopPropsResolved} />
                <Line
                  type="monotone"
                  dataKey="observados"
                  name="Observados (histórico)"
                  stroke="#0f766e"
                  strokeWidth={2.5}
                  dot={{ r: 3 }}
                  connectNulls={false}
                />
                <Line
                  type="linear"
                  dataKey="ajuste"
                  name={modeloLegendLabel(metaActiva.modelo)}
                  stroke="#c2410c"
                  strokeWidth={2}
                  strokeDasharray="6 4"
                  dot={{ r: 2 }}
                  connectNulls
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}

      <section className="panel prioridad-territorial-panel predicciones-seccion">
        <h2>2. Prioridad territorial (índice compuesto)</h2>
        <p className="muted small">
          Ranking descriptivo (P05): fórmula <strong>fija</strong> (sin selector de modelo como en las secciones 1,
          3 y 4). Combina frecuencia, densidad/km², delta de promedios, gravedad y participación. Elija{' '}
          <strong>nivel territorial</strong> (comuna o barrio) y, si quiere contrastar, «Ordenar por» índice o solo
          volumen.
        </p>
        {prioridad?.meta && <PrioridadNotasContexto meta={prioridad.meta} />}
        {prioridad?.meta && <PrioridadAlertaLiderazgo meta={prioridad.meta} />}
        {prioridad?.meta && <PrioridadPesosAyuda meta={prioridad.meta} />}
        {prioridad?.meta && <PrioridadSensibilidadAyuda meta={prioridad.meta} />}
        <PrioridadColumnasAyuda />
        {prioridad?.meta && (
          <PrioridadInterpretacionComponentesGuia
            meta={prioridad.meta}
            filaLider={prioridadFilas[0]}
            nivel={prioridadNivelDatos}
          />
        )}
        <div className="filter-grid" style={{ marginBottom: 12 }}>
          <label className="filter-field">
            Nivel territorial
            <select value={nivelPrioridad} onChange={(e) => setNivelPrioridad(e.target.value)}>
              <option value="comuna">Comuna</option>
              <option value="barrio" disabled={Boolean(barrioId)}>
                Barrio
              </option>
            </select>
          </label>
          <label className="filter-field">
            Ordenar por
            <select value={ordenPrioridad} onChange={(e) => setOrdenPrioridad(e.target.value)}>
              <option value="compuesto">Índice compuesto</option>
              <option value="frecuencia">Solo por frecuencia (incidentes)</option>
            </select>
          </label>
        </div>
        {ordenPrioridad === 'compuesto' && (
          <p className="muted small">
            La columna «# vol.» muestra el puesto del territorio si solo se ordenara por número de
            incidentes; sirve para contrastar con el índice compuesto.
          </p>
        )}
        {prioridad?.meta?.formula && (
          <p className="muted small">
            <strong>Fórmula:</strong> {prioridad.meta.formula}
          </p>
        )}
        {prioridad?.meta?.limitaciones && (
          <p className="muted small">{prioridad.meta.limitaciones}</p>
        )}
        {prioridad?.meta?.sin_datos && (
          <p className="muted">No hay territorios con volumen suficiente en este rango y filtros.</p>
        )}
        {prioridadFilas.length > 0 && (
          <div className="prioridad-table-wrap">
            <table className="prioridad-table prioridad-table-ampliada">
              <thead>
                <tr>
                  {PRIORIDAD_COLUMNAS_AYUDA.filter((c) => c.col !== '# vol.' || mostrarColVol).map(
                    (c) => (
                    <th key={c.col} title={c.texto}>
                      {c.col === 'Territorio'
                        ? prioridadNivelDatos === 'comuna'
                          ? 'Comuna'
                          : 'Barrio'
                        : c.col === '#'
                          ? ordenPrioridad === 'frecuencia'
                            ? '# (volumen)'
                            : '# (índice)'
                          : c.col}
                    </th>
                  ),
                  )}
                </tr>
              </thead>
              <tbody>
                {prioridadFilas.map((row) => (
                  <tr key={`${row.rank}-${row.comuna_id ?? row.barrio_id}`}>
                    <td>{row.rank}</td>
                    {mostrarColVol ? <td>{row.rank_frecuencia ?? '—'}</td> : null}
                    <td>{nombreTerritorioPrioridad(row, prioridadNivelDatos)}</td>
                    <td>
                      <strong>{row.indice_prioridad}</strong>
                    </td>
                    <td>
                      <span className={`prioridad-chip prioridad-${row.nivel_prioridad}`}>
                        {row.nivel_prioridad}
                      </span>
                    </td>
                    <td>{row.incidentes_periodo?.toLocaleString('es-CO')}</td>
                    <td>
                      {row.densidad_incidentes_km2 != null
                        ? row.densidad_incidentes_km2.toLocaleString('es-CO', {
                            maximumFractionDigits: 2,
                          })
                        : '—'}
                    </td>
                    <td>{row.pct_victimas_fatales}%</td>
                    <td>
                      {(row.delta_promedio_incidentes ?? row.pendiente_mensual_incidentes) != null
                        ? (row.delta_promedio_incidentes ?? row.pendiente_mensual_incidentes).toLocaleString(
                            'es-CO',
                            { maximumFractionDigits: 2 },
                          )
                        : '—'}
                    </td>
                    <td>{row.participacion_incidentes_pct}%</td>
                    <td>
                      <PrioridadComponentesCelda
                        componentes={row.componentes_normalizados}
                        tendenciaAtenuada={row.tendencia_atenuada}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {!prioridad && !loading && !err && (
          <p className="muted small">Pulse Actualizar para calcular el ranking.</p>
        )}
      </section>

      <section className="panel carga-comparativa-panel predicciones-seccion">
        <h2>
          3. Comparación territorial de carga proyectada (P08 · P09/P10)
          {loadingCarga && <span className="muted small"> — actualizando…</span>}
        </h2>
        <p className="muted small">
          <strong>Qué mide:</strong>{' '}
          {cargaEsperada?.meta?.que_mide ??
            'Volumen futuro esperado de incidentes por territorio (suma del horizonte de predicciones).'}
          {' '}
          Las barras comparan los principales {nivelCarga === 'barrio' ? 'barrios (P10)' : 'comunas (P09)'}; el
          color indica la categoría P08 (alto / medio / bajo por terciles).
        </p>
        <p className="muted small">
          <strong>Vs. P05:</strong>{' '}
          {cargaEsperada?.meta?.diferencia_p05 ??
            'P05 mezcla historial y gravedad; P08 solo proyecta incidentes hacia adelante.'}
        </p>
        <div className="seccion-controles-stack">
          <div className="predicciones-toolbar seccion-modelo-toolbar">
            <label>
              Nivel territorial
              <select
                className="predicciones-select"
                value={nivelCarga}
                onChange={(e) => setNivelCarga(e.target.value)}
                disabled={loadingCarga}
              >
                <option value="comuna">Comuna (P09)</option>
                <option value="barrio">Barrio (P10)</option>
              </select>
            </label>
          </div>
          <SeccionModeloToolbar
            modelo={modeloCarga}
            onModeloChange={setModeloCarga}
            opciones={MODELO_CARGA_OPTS}
            ventanaMa={ventanaMaCarga}
            onVentanaMaChange={setVentanaMaCarga}
            horizonte={horizonteCarga}
            onHorizonteChange={setHorizonteCarga}
            loading={loadingCarga}
            horizonteId="horizonte-carga"
            arimaOrder={arimaOrderCarga}
            onArimaOrderChange={setArimaOrderCarga}
            sarimaSeasonal={sarimaSeasonalCarga}
            onSarimaSeasonalChange={setSarimaSeasonalCarga}
          />
        </div>
        <p className="muted small seccion-modelo-hint">
          Cambios de <strong>nivel</strong>, <strong>modelo</strong> u <strong>horizonte</strong> recalculan solo esta
          sección.
        </p>
        <CargaBondadPanel meta={cargaEsperada?.meta} />
        {cargaEsperada?.meta?.alerta_liderazgo?.mensaje && (
          <p className="warn small prioridad-alerta-liderazgo" role="status">
            {cargaEsperada.meta.alerta_liderazgo.mensaje}
          </p>
        )}
        {cargaEsperada?.meta?.metodo && !cargaEsperada.meta.sin_datos && (
          <p className="muted small">
            <strong>Cálculo:</strong> {cargaEsperada.meta.metodo}
          </p>
        )}
        {cargaEsperada?.meta?.interpretacion && (
          <p className="bondad-interpretacion bondad-moderado carga-interpretacion" role="status">
            <strong>Interpretación:</strong> {cargaEsperada.meta.interpretacion}
          </p>
        )}
        {cargaEsperada?.meta?.limitaciones && (
          <p className="muted small carga-limitaciones">{cargaEsperada.meta.limitaciones}</p>
        )}
        {cargaEsperada?.meta?.sin_datos && (
          <p className="warn small">No hay territorios con serie suficiente para proyectar carga.</p>
        )}
        {cargaComparativaData.length > 0 && (
          <>
            <div className="carga-comparativa-leyenda" aria-hidden="true">
              <span>
                <span className="carga-leyenda-muestra" style={{ background: CARGA_CATEGORIA_COLOR.alto }} /> Alto
              </span>
              <span>
                <span className="carga-leyenda-muestra" style={{ background: CARGA_CATEGORIA_COLOR.medio }} /> Medio
              </span>
              <span>
                <span className="carga-leyenda-muestra" style={{ background: CARGA_CATEGORIA_COLOR.bajo }} /> Bajo
              </span>
            </div>
            <div className="chart-wrap carga-comparativa-chart">
              <ResponsiveContainer width="100%" height={cargaBarHeight}>
                <BarChart
                  layout="vertical"
                  data={cargaComparativaData}
                  margin={
                    chartLayoutCompact
                      ? { top: 8, right: 12, left: 4, bottom: 8 }
                      : { top: 12, right: 24, left: 8, bottom: 12 }
                  }
                  barCategoryGap="14%"
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" horizontal={false} />
                  <XAxis
                    type="number"
                    allowDecimals={false}
                    tick={{ fontSize: chartLayoutCompact ? 10 : 11 }}
                  />
                  <YAxis
                    type="category"
                    dataKey="nombre"
                    width={chartLayoutCompact ? 108 : 140}
                    tick={{ fontSize: chartLayoutCompact ? 9 : 10 }}
                    interval={0}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.length) return null
                      const row = payload[0].payload
                      return (
                        <div
                          className="recharts-default-tooltip"
                          style={{
                            padding: '8px 12px',
                            background: '#fff',
                            border: '1px solid #e2e8f0',
                            borderRadius: 8,
                          }}
                        >
                          <p className="small" style={{ marginBottom: 6, fontWeight: 600 }}>
                            #{row.rank} · {row.nombre}
                          </p>
                          <p className="small muted" style={{ margin: '2px 0' }}>
                            Carga proyectada:{' '}
                            <strong>
                              {row.carga.toLocaleString('es-CO', { maximumFractionDigits: 1 })}
                            </strong>
                          </p>
                          <p className="small muted" style={{ margin: '2px 0' }}>
                            Categoría P08: <strong>{row.categoria}</strong>
                          </p>
                          <p className="small muted" style={{ margin: '2px 0' }}>
                            Incidentes en periodo: <strong>{row.incidentes}</strong>
                          </p>
                        </div>
                      )
                    }}
                  />
                  <Bar dataKey="carga" name="Carga proyectada (horizonte)" radius={[0, 4, 4, 0]}>
                    {cargaComparativaData.map((entry) => (
                      <Cell
                        key={`${entry.rank}-${entry.nombre}`}
                        fill={CARGA_CATEGORIA_COLOR[entry.categoria] ?? CARGA_CATEGORIA_COLOR.bajo}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <details className="carga-tabla-detalle">
              <summary className="small muted">Ver tabla detallada</summary>
              <div className="prioridad-table-wrap">
                <table className="prioridad-table">
                  <thead>
                    <tr>
                      <th>#</th>
                      <th># vol.</th>
                      <th>{nivelCarga === 'barrio' ? 'Barrio' : 'Comuna'}</th>
                      <th>Carga proyectada</th>
                      <th>Categoría</th>
                      <th>Incidentes periodo</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(cargaEsperada?.ranking || []).map((row) => (
                      <tr key={row.rank}>
                        <td>{row.rank}</td>
                        <td>{row.rank_frecuencia ?? '—'}</td>
                        <td>
                          {nivelCarga === 'barrio' ? row.barrio_nombre : row.comuna_nombre}
                          {nivelCarga === 'barrio' && row.comuna_nombre && (
                            <span className="muted small"> ({row.comuna_nombre})</span>
                          )}
                        </td>
                        <td>
                          {row.carga_proyectada_horizonte?.toLocaleString('es-CO', {
                            maximumFractionDigits: 1,
                          })}
                        </td>
                        <td>
                          <span className={`prioridad-chip prioridad-${row.categoria_esperada}`}>
                            {row.categoria_esperada}
                          </span>
                        </td>
                        <td>{row.incidentes_periodo}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </>
        )}
      </section>

      <section className="panel proporcion-fatales-panel predicciones-seccion">
        <h2>
          4. Proporción de víctimas fatales (P07)
          {loadingProporcion && <span className="muted small"> — actualizando…</span>}
        </h2>
        <p className="muted small">
          <strong>Qué mide:</strong> de las víctimas de cada mes, qué porcentaje fue fatal. Es una forma de
          ver si el periodo fue <em>más o menos grave de lo habitual</em>, no cuántos hechos ocurrirán.
          Usa los mismos filtros de fechas y territorio que el resto de la página.
        </p>
        <ProporcionGuiaInterpretacion />
        {metaProporcion?.metodo && (
          <p className="muted small">
            <strong>Método ({MODELO_PROP_OPTS.find((o) => o.value === metaProporcion.modelo)?.label ?? metaProporcion.modelo}):</strong>{' '}
            {metaProporcion.metodo}
          </p>
        )}
        {metaProporcion?.leyenda_grafico && (
          <p className="muted small">
            <strong>Lectura del gráfico:</strong> {metaProporcion.leyenda_grafico}
          </p>
        )}
        <ProporcionUmbralesR2 meta={metaProporcion} />
        <SeccionModeloToolbar
          modelo={modeloProp}
          onModeloChange={setModeloProp}
          opciones={opcionesModeloProp}
          ventanaMa={ventanaMaProp}
          onVentanaMaChange={setVentanaMaProp}
          horizonte={horizonteProp}
          onHorizonteChange={setHorizonteProp}
          loading={loadingProporcion}
          horizonteId="horizonte-proporcion"
          arimaOrder={arimaOrderProp}
          onArimaOrderChange={setArimaOrderProp}
          sarimaSeasonal={sarimaSeasonalProp}
          onSarimaSeasonalChange={setSarimaSeasonalProp}
        >
          <label>
            Meses de prueba
            <select
              className="predicciones-select"
              value={holdoutMesesProp}
              disabled={loadingProporcion}
              onChange={(e) => setHoldoutMesesProp(Number(e.target.value))}
            >
              {HOLDOUT_MESES_OPTS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          {!comunaId && (
            <label className="checkbox-inline">
              <input
                type="checkbox"
                checked={desgloseComunaProp}
                disabled={loadingProporcion}
                onChange={(e) => setDesgloseComunaProp(e.target.checked)}
              />
              Desglose por comuna (top 10)
            </label>
          )}
          <label className="checkbox-inline">
            <input
              type="checkbox"
              checked={modelosAvanzadosProp}
              disabled={loadingProporcion}
              onChange={(e) => setModelosAvanzadosProp(e.target.checked)}
            />
            Modelos avanzados (OLS, logit, ARIMA)
          </label>
        </SeccionModeloToolbar>
        <p className="muted small seccion-modelo-hint">
          El modelo y el horizonte de este bloque no afectan la proyección mensual de arriba. La prueba aparta
          los últimos meses del ajuste y comprueba si el modelo habría acertado el porcentaje.
        </p>
        {metaProporcion?.n_meses_ajuste != null && (
          <p className="muted small">
            <strong>Meses en el ajuste:</strong> {metaProporcion.n_meses_ajuste}
            {metaProporcion.n_meses_con_pct_observado != null
              ? ` · con % observado: ${metaProporcion.n_meses_con_pct_observado}`
              : ''}
            .
          </p>
        )}
        {metaProporcion?.aviso_rango_corto && (
          <p className="warn small" role="status">
            {metaProporcion.aviso_rango_corto}
          </p>
        )}
        {metaProporcion?.limitaciones && (
          <p className="muted small">{metaProporcion.limitaciones}</p>
        )}
        {metaProporcion?.sin_modelo ? (
          <p className="warn small" role="status">
            Serie insuficiente para ajustar: se requieren al menos{' '}
            <strong>{minMesesModelo(metaProporcion.modelo, metaProporcion.ventana_meses)} meses</strong> con ≥
            10 víctimas en el rango. Amplíe fechas o quite filtros estrechos.
          </p>
        ) : (
          <>
            <ProporcionBondadVisible meta={metaProporcion} />
            <BondadConsejoModelo meta={metaProporcion} />
            <HoldoutEvaluacionPanel meta={metaProporcion} unidadPct />
            <p className="muted small">
              <ProporcionCoefResumen meta={metaProporcion} />
            </p>
            <BondadInterpretacion meta={metaProporcion} />
          </>
        )}
        {proporcion?.meta?.desglose_comuna && proporcion.series_por_comuna?.length > 0 && (
          <label>
            Comuna
            <select
              className="predicciones-select"
              value={serieComunaIdx}
              onChange={(e) => setSerieComunaIdx(Number(e.target.value))}
            >
              {proporcion.series_por_comuna.map((s, i) => (
                <option key={s.comuna_id ?? i} value={i}>
                  {s.comuna_nombre}
                </option>
              ))}
            </select>
          </label>
        )}
        {proporcionLineData.length > 0 && (
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height={prediccionesChartHeight}>
              <ComposedChart data={proporcionLineData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="mes" tick={{ fontSize: 11 }} />
                <YAxis
                  domain={[0, 'auto']}
                  tickFormatter={(v) => `${v}%`}
                  width={yAxisTickWidth}
                />
                <Tooltip
                  formatter={(v, name) =>
                    v != null
                      ? [`${v}%`, name]
                      : ['—', name]
                  }
                />
                <Legend {...legendTopPropsResolved} />
                <Area
                  type="monotone"
                  dataKey="bandaSup"
                  name="Banda sup. (~95 %)"
                  stroke="none"
                  fill="#fecaca"
                  fillOpacity={0.35}
                  connectNulls={false}
                  legendType="none"
                />
                <Area
                  type="monotone"
                  dataKey="bandaInf"
                  name="Banda inf."
                  stroke="none"
                  fill="#ffffff"
                  fillOpacity={1}
                  connectNulls={false}
                  legendType="none"
                />
                <Line
                  type="monotone"
                  dataKey="pct"
                  name="% observado"
                  stroke="#2563eb"
                  dot={{ r: 3 }}
                  connectNulls={false}
                />
                <Line
                  type="monotone"
                  dataKey="ajuste"
                  name="Ajuste / proyección %"
                  stroke="#dc2626"
                  strokeDasharray="6 4"
                  dot={{ r: 2 }}
                  connectNulls={false}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      <section className="panel predicciones-seccion patrones-seccion-controles">
        <h2>
          5. Patrones día × hora y día de semana (P12 · P13)
          {loadingPatrones && <span className="muted small"> — actualizando…</span>}
        </h2>
        <p className="muted small">
          Indica <strong>en qué momentos de la semana</strong> se concentraría la carga de incidentes
          del horizonte proyectado, según cómo se distribuyeron en el periodo filtrado. El total sale del
          mismo modelo y horizonte que la proyección mensual (bloque 1), siempre contando incidentes.
        </p>
        <PatronesGuiaInterpretacion />
        <p className="muted small seccion-modelo-hint patrones-enlace-bloque1">
          Modelo y horizonte: los de la sección <strong>1. Proyección mensual</strong> (
          {MODELO_OPTS.find((o) => o.value === modeloPred)?.label ?? modeloPred},{' '}
          {horizontePred} {horizontePred === 1 ? 'mes' : 'meses'}). Al cambiarlos allí se actualizan
          automáticamente la matriz y las barras por día.
        </p>
      </section>

      <RouteErrorBoundary>
        <PatronesDiaHoraPanel
          matrizProyectada={matrizProyectada}
          diaSemanaProyectado={diaSemanaProyectado}
          loading={loadingPatrones}
          horizonteMeses={horizontePred}
        />
      </RouteErrorBoundary>
    </div>
  )
}
