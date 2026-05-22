import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'
import { Link } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
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
]

const VARIABLE_OPTS = [
  { value: 'incidentes', label: 'Incidentes' },
  { value: 'victimas', label: 'Víctimas' },
  { value: 'victimas_fatales', label: 'Víctimas fatales' },
]

const MODELO_PROP_OPTS = [
  { value: 'estacional', label: 'Estacional sobre % (recomendado)' },
  { value: 'ols', label: 'OLS sobre % mensual' },
  { value: 'logistica', label: 'Logit-lineal (tendencia en escala logit)' },
]

const MODELO_CARGA_OPTS = [
  { value: 'estacional', label: 'Estacional (recomendado)' },
  { value: 'ols', label: 'OLS (tendencia)' },
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
  return 'Tendencia OLS + extrapolación'
}

function minMesesModelo(modelo) {
  return modelo === 'ols' ? 'dos' : 'tres'
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

const PRIORIDAD_COLUMNAS_AYUDA = [
  {
    col: '#',
    titulo: 'Posición (#)',
    texto: 'Orden del ranking: 1 = mayor índice de prioridad con los filtros y fechas actuales.',
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
      'Puntaje 0–100 aprox. que combina frecuencia, tendencia al alza, % víctimas fatales y participación. No es el número de incidentes.',
  },
  {
    col: 'Nivel',
    titulo: 'Nivel de prioridad',
    texto:
      'Alto / medio / bajo según terciles del índice entre los territorios de esta tabla (comparación relativa, no umbral fijo de la ciudad).',
  },
  {
    col: 'Incidentes',
    titulo: 'Incidentes en el periodo',
    texto: 'Conteo de incidentes distintos entre las fechas «Desde» y «Hasta» (y filtros aplicados).',
  },
  {
    col: '% fatales',
    titulo: '% víctimas fatales',
    texto:
      'Porcentaje de víctimas registradas en ese territorio que fueron clasificadas como fatales (misma regla que los KPIs del tablero).',
  },
  {
    col: 'Pendiente/mes',
    titulo: 'Pendiente mensual (OLS)',
    texto:
      'Cambio promedio de incidentes por mes según una recta OLS sobre la serie mensual. Positivo = empeora; negativo = mejora. Solo las pendientes ≥ 0 suman al componente «tendencia» del índice. No usa el modelo estacional (ese está en el gráfico de arriba).',
  },
  {
    col: 'Part. %',
    titulo: 'Participación %',
    texto:
      'Porcentaje de todos los incidentes del periodo (mismos filtros, vista global) que ocurrieron en este territorio.',
  },
]

function PrioridadPesosAyuda({ meta }) {
  const items = meta?.justificacion_pesos
  const tend = meta?.tendencia_componente
  if (!items?.length) return null
  return (
    <details className="prioridad-ayuda-details">
      <summary>¿Por qué estos pesos y OLS en la tendencia?</summary>
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
            <strong>Tendencia en la tabla:</strong> {tend.etiqueta}. {tend.por_que_ols}
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
    <details className="prioridad-ayuda-details" open>
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
  return (
    <>
      OLS del %: pendiente ≈ <strong>{c.pendiente_b_mes ?? '—'}</strong> puntos porcentuales/mes. {bondad}
    </>
  )
}

function ProporcionUmbralesR2({ meta }) {
  const u = meta?.umbrales_r2_p07
  if (!u) return null
  return (
    <p className="muted small proporcion-umbrales-r2">
      <strong>R² orientativo (P07):</strong> bueno {u.bueno}; moderado {u.moderado}; bajo {u.bajo}.
    </p>
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

  const [predicciones, setPredicciones] = useState(null)
  const [horizontePredicciones, setHorizontePredicciones] = useState(3)
  const [modeloPred, setModeloPred] = useState('ols')
  const [variablePred, setVariablePred] = useState('incidentes')
  const [desglosePorClase, setDesglosePorClase] = useState(false)
  const [excluirCovid, setExcluirCovid] = useState(true)
  const [serieClaseIdx, setSerieClaseIdx] = useState(0)
  const [nivelPrioridad, setNivelPrioridad] = useState('comuna')
  const [prioridad, setPrioridad] = useState(null)
  const [modeloProp, setModeloProp] = useState('estacional')
  const [desgloseComunaProp, setDesgloseComunaProp] = useState(false)
  const [serieComunaIdx, setSerieComunaIdx] = useState(0)
  const [proporcion, setProporcion] = useState(null)
  const [nivelCarga, setNivelCarga] = useState('comuna')
  const [modeloCarga, setModeloCarga] = useState('estacional')
  const [cargaEsperada, setCargaEsperada] = useState(null)
  const [matrizProyectada, setMatrizProyectada] = useState(null)
  const [diaSemanaProyectado, setDiaSemanaProyectado] = useState(null)
  const [loadingProporcion, setLoadingProporcion] = useState(false)
  const [loadingCarga, setLoadingCarga] = useState(false)
  const [loadingPatrones, setLoadingPatrones] = useState(false)
  const [err, setErr] = useState(null)
  const [loading, setLoading] = useState(true)
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
    }),
    [desde, hasta, comunaId, barrioId, claseId],
  )

  const prediccionesQuery = useCallback(
    () => ({
      ...filtrosQuery(),
      horizonte_meses: horizontePredicciones,
      modelo: modeloPred,
      variable: variablePred,
      ...(desglosePorClase && !claseId ? { desglose_clase: '1' } : {}),
      ...(excluirCovid ? { excluir_covid: '1' } : {}),
    }),
    [
      filtrosQuery,
      horizontePredicciones,
      modeloPred,
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

  const proporcionQuery = useCallback(
    () => ({
      ...filtrosQuery(),
      horizonte_meses: horizontePredicciones,
      modelo: modeloProp,
      ...(desgloseComunaProp && !comunaId ? { desglose_comuna: '1' } : {}),
      ...(excluirCovid ? { excluir_covid: '1' } : {}),
    }),
    [
      filtrosQuery,
      horizontePredicciones,
      modeloProp,
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
      horizonte_meses: horizontePredicciones,
      modelo: modeloCarga,
      ...(excluirCovid ? { excluir_covid: '1' } : {}),
    }),
    [filtrosQuery, nivelCarga, horizontePredicciones, modeloCarga, excluirCovid],
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
  }, [modeloProp, desgloseComunaProp, loadProporcion])

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
  }, [nivelCarga, modeloCarga, horizontePredicciones, loadCarga])

  const patronesQuery = useCallback(
    () => ({
      ...filtrosQuery(),
      horizonte_meses: horizontePredicciones,
      modelo: modeloCarga,
      ...(excluirCovid ? { excluir_covid: '1' } : {}),
    }),
    [filtrosQuery, horizontePredicciones, modeloCarga, excluirCovid],
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
  }, [horizontePredicciones, modeloCarga, loadPatrones, predicciones])

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
          modelo: 'estacional',
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
      <header className="page-intro">
        <h1>Predicciones</h1>
        <p className="muted">
          Proyección mensual (Fase A), prioridad y carga territorial (P05–P10), proporción de fatales (P07) y patrones
          día×hora / día de semana (P12–P13): comparan el <strong>periodo seleccionado</strong> con la{' '}
          <strong>proyección</strong> en el horizonte. El ranking de vías (P11) está en el{' '}
          <Link to="/tablero">Tablero</Link>.
        </p>
      </header>

      {loading && !predicciones && !err && <p className="muted">Cargando rango de fechas y serie…</p>}

      <section className="panel filter-panel">
        <h2>Filtros del periodo y territorio</h2>
        <p className="muted small filter-help">
          El periodo por defecto es el <strong>último año con registros</strong> en base. Ajuste fechas, comuna, barrio
          o clase y pulse <strong>Actualizar</strong>.
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
            Variable
            <select value={variablePred} onChange={(e) => setVariablePred(e.target.value)}>
              {VARIABLE_OPTS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            Modelo
            <select value={modeloPred} onChange={(e) => setModeloPred(e.target.value)}>
              {MODELO_OPTS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field filter-field-checkbox">
            <input
              type="checkbox"
              checked={desglosePorClase}
              disabled={Boolean(claseId)}
              onChange={(e) => {
                setDesglosePorClase(e.target.checked)
                setSerieClaseIdx(0)
              }}
            />
            Desglose por clase (hasta 15 clases con más datos)
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
        <section className="panel chart-panel-comparativo">
          <h2>
            Predicciones — {metaActiva.variable_etiqueta || 'serie mensual'}
            {predicciones.meta?.desglose_clase ? ' (por clase)' : ''}
          </h2>
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
              Hay menos de <strong>{minMesesModelo(metaActiva.modelo)} meses</strong> con datos en el rango; no se
              calcula proyección. Amplíe las fechas o verifique datos.
            </p>
          ) : (
            <>
              <p className="muted small">
                <CoefResumen meta={metaActiva} />
              </p>
              <BondadInterpretacion meta={metaActiva} />
            </>
          )}
          <div className="predicciones-toolbar">
            <label className="muted small" htmlFor="horizonte-pred-page">
              Meses a proyectar (después del último mes del rango):
            </label>
            <select
              id="horizonte-pred-page"
              className="predicciones-select"
              value={String(horizontePredicciones)}
              disabled={loading}
              onChange={(e) => {
                const v = Math.min(12, Math.max(1, Number(e.target.value) || 3))
                setHorizontePredicciones(v)
                ;(async () => {
                  try {
                    const r = await fetchDashboardPrediccionesMensuales({
                      ...prediccionesQuery(),
                      horizonte_meses: v,
                    })
                    setPredicciones(r)
                  } catch {
                    setPredicciones(null)
                  }
                })()
              }}
            >
              {Array.from({ length: 12 }, (_, i) => i + 1).map((n) => (
                <option key={n} value={String(n)}>
                  {n}
                </option>
              ))}
            </select>
          </div>
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

      <section className="panel prioridad-territorial-panel">
        <h2>Prioridad territorial (índice compuesto)</h2>
        <p className="muted small">
          Ranking descriptivo (P05): puntaje compuesto para comparar territorios en el periodo filtrado. No
          sustituye el gráfico de proyección mensual de arriba (allí puede usarse el modelo estacional).
        </p>
        {prioridad?.meta && <PrioridadPesosAyuda meta={prioridad.meta} />}
        <PrioridadColumnasAyuda />
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
        </div>
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
        {prioridad?.ranking?.length > 0 && (
          <div className="prioridad-table-wrap">
            <table className="prioridad-table">
              <thead>
                <tr>
                  {PRIORIDAD_COLUMNAS_AYUDA.map((c) => (
                    <th key={c.col} title={c.texto}>
                      {c.col === 'Territorio'
                        ? nivelPrioridad === 'comuna'
                          ? 'Comuna'
                          : 'Barrio'
                        : c.col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {prioridad.ranking.map((row) => (
                  <tr key={row.rank}>
                    <td>{row.rank}</td>
                    <td>
                      {nivelPrioridad === 'comuna'
                        ? row.comuna_nombre
                        : `${row.barrio_nombre}${row.comuna_nombre ? ` (${row.comuna_nombre})` : ''}`}
                    </td>
                    <td>
                      <strong>{row.indice_prioridad}</strong>
                    </td>
                    <td>
                      <span className={`prioridad-chip prioridad-${row.nivel_prioridad}`}>
                        {row.nivel_prioridad}
                      </span>
                    </td>
                    <td>{row.incidentes_periodo?.toLocaleString('es-CO')}</td>
                    <td>{row.pct_victimas_fatales}%</td>
                    <td>
                      {row.pendiente_mensual_incidentes != null
                        ? row.pendiente_mensual_incidentes.toLocaleString('es-CO', {
                            maximumFractionDigits: 2,
                          })
                        : '—'}
                    </td>
                    <td>{row.participacion_incidentes_pct}%</td>
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

      <section className="panel proporcion-fatales-panel">
        <h2>
          Proporción de víctimas fatales (P07)
          {loadingProporcion && <span className="muted small"> — actualizando…</span>}
        </h2>
        <p className="muted small">
          <strong>Qué mide:</strong> gravedad relativa mes a mes — % de víctimas del mes que fueron
          fatales (<code>fatales / víctimas × 100</code>), con los mismos filtros de fecha y territorio que
          arriba. Complementa el volumen de incidentes/víctimas del bloque superior.
        </p>
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
        <div className="predicciones-toolbar">
          <label>
            Modelo
            <select
              className="predicciones-select"
              value={modeloProp}
              onChange={(e) => setModeloProp(e.target.value)}
            >
              {MODELO_PROP_OPTS.map((o) => (
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
                onChange={(e) => setDesgloseComunaProp(e.target.checked)}
              />
              Desglose por comuna (top 10)
            </label>
          )}
        </div>
        {metaProporcion?.limitaciones && (
          <p className="muted small">{metaProporcion.limitaciones}</p>
        )}
        {metaProporcion?.sin_modelo ? (
          <p className="warn small" role="status">
            Serie insuficiente para ajustar (pocos meses con ≥ 10 víctimas). Amplíe fechas o quite filtros
            estrechos.
          </p>
        ) : (
          <>
            <ProporcionBondadVisible meta={metaProporcion} />
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
              <LineChart data={proporcionLineData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="mes" tick={{ fontSize: 11 }} />
                <YAxis
                  domain={[0, 'auto']}
                  tickFormatter={(v) => `${v}%`}
                  width={yAxisTickWidth}
                />
                <Tooltip formatter={(v) => (v != null ? `${v}%` : '—')} />
                <Legend {...legendTopPropsResolved} />
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
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      <section className="panel carga-comparativa-panel">
        <h2>
          Comparación territorial de carga proyectada (P08 · P09/P10)
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
          {' '}
          El ranking de <strong>vías y puntos críticos (P11)</strong> está en el{' '}
          <Link to="/tablero">Tablero</Link>.
        </p>
        <div className="predicciones-toolbar">
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
          <label>
            Modelo proyección
            <select
              className="predicciones-select"
              value={modeloCarga}
              onChange={(e) => setModeloCarga(e.target.value)}
              disabled={loadingCarga}
            >
              {MODELO_CARGA_OPTS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="muted small">
          Cambios de <strong>nivel</strong>, <strong>modelo</strong> o <strong>horizonte</strong> (filtros
          superiores) actualizan el gráfico sin pulsar Actualizar. Fechas y filtros de territorio sí
          requieren Actualizar.
        </p>
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

      <RouteErrorBoundary>
        <PatronesDiaHoraPanel
          matrizProyectada={matrizProyectada}
          diaSemanaProyectado={diaSemanaProyectado}
          loading={loadingPatrones}
          horizonteMeses={horizontePredicciones}
        />
      </RouteErrorBoundary>
    </div>
  )
}
