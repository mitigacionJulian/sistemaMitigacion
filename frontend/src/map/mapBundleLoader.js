import {
  fetchDashboardCalidadTerritorio,
  fetchDashboardChoroplethTerritorial,
  fetchDashboardDensidadTerritorial,
  fetchDashboardHotspotsCuadricula,
  fetchDashboardHotspotsRanking,
  fetchDashboardMapaDetalle,
} from '../api/client.js'
import {
  choroplethCacheKey,
  createEmptyBundle,
  detalleCacheKey,
  hotspotsCacheKey,
} from './mapPageCache.js'

const DEFAULT_DETALLE_LIMITE = 10000
const CHOROPLETH_NIVELES = ['comuna', 'barrio']
const CHOROPLETH_METRICAS = ['densidad', 'conteo']
const CELDA_SIZES = ['300', '500']

/**
 * @param {(state: { percent: number, label: string, step?: number, totalSteps?: number }) => void} onProgress
 */
async function runStep(onProgress, stepIndex, totalSteps, label, fn) {
  onProgress?.({
    percent: Math.min(99, Math.round((stepIndex / totalSteps) * 100)),
    label,
    step: stepIndex,
    totalSteps,
  })
  const result = await fn()
  onProgress?.({
    percent: Math.min(99, Math.round(((stepIndex + 1) / totalSteps) * 100)),
    label,
    step: stepIndex + 1,
    totalSteps,
  })
  return result
}

/**
 * Precalienta todas las capas e indicadores para una combinación de filtros.
 * @param {object} baseParams — desde/hasta + ids API
 * @param {import('./mapPageCache.js').MapFilterBundle} bundle
 * @param {{ onProgress?: Function, includeDetalle?: boolean }} options
 */
export async function warmFilterBundle(baseParams, bundle, options = {}) {
  const { onProgress, includeDetalle = true } = options
  const totalSteps = includeDetalle ? 7 : 6
  let step = 0

  await runStep(onProgress, step++, totalSteps, 'Coropleta por comuna y barrio (densidad y conteo)…', async () => {
    await Promise.all(
      CHOROPLETH_NIVELES.flatMap((nivel) =>
        CHOROPLETH_METRICAS.map(async (metrica) => {
          const data = await fetchDashboardChoroplethTerritorial({
            ...baseParams,
            nivel,
            metrica,
          })
          bundle.choropleth[choroplethCacheKey(nivel, metrica)] = data
        }),
      ),
    )
  })

  await runStep(onProgress, step++, totalSteps, 'Calidad territorial (G03)…', async () => {
    bundle.calidad = await fetchDashboardCalidadTerritorio({
      ...baseParams,
      limite_ejemplos: 5,
    })
  })

  await runStep(onProgress, step++, totalSteps, 'Densidad territorial por comuna y barrio…', async () => {
    const [comuna, barrio] = await Promise.all([
      fetchDashboardDensidadTerritorial({ ...baseParams, nivel: 'comuna', limite: 12 }),
      fetchDashboardDensidadTerritorial({ ...baseParams, nivel: 'barrio', limite: 12 }),
    ])
    bundle.densidad.comuna = comuna
    bundle.densidad.barrio = barrio
  })

  await runStep(onProgress, step++, totalSteps, 'Ranking de celdas calientes (G06)…', async () => {
    await Promise.all(
      CELDA_SIZES.map(async (tamano) => {
        bundle.ranking[tamano] = await fetchDashboardHotspotsRanking({
          ...baseParams,
          tamano_celda_m: Number(tamano),
          limite: 10,
          orden: 'densidad',
        })
      }),
    )
  })

  await runStep(onProgress, step++, totalSteps, 'Cuadrícula hotspots P14 (300 m y 500 m)…', async () => {
    await Promise.all(
      CELDA_SIZES.map(async (tamano) => {
        bundle.hotspots[hotspotsCacheKey(tamano, 'cuadricula')] =
          await fetchDashboardHotspotsCuadricula({
            ...baseParams,
            metodo: 'cuadricula',
            tamano_celda_m: Number(tamano),
          })
      }),
    )
  })

  if (includeDetalle) {
    await runStep(onProgress, step++, totalSteps, 'Detalle de incidentes (muestra amplia)…', async () => {
      const nivel =
        baseParams.barrio_id != null ? 'barrio' : baseParams.comuna_id != null ? 'barrio' : 'comuna'
      const detalle = await fetchDashboardMapaDetalle({
        ...baseParams,
        nivel,
        metrica: 'densidad',
        limite: DEFAULT_DETALLE_LIMITE,
      })
      bundle.detalle[detalleCacheKey(DEFAULT_DETALLE_LIMITE)] = {
        choropleth: detalle.choropleth,
        puntos: detalle.puntos,
        puntos_meta: detalle.puntos_meta,
      }
    })
  }

  bundle.warmedAt = Date.now()
  onProgress?.({ percent: 100, label: 'Listo', step: totalSteps, totalSteps })
  return bundle
}

/** Carga solo la capa que falta (cambio de modo sin recalentar todo el paquete). */
function hotspotsFetchParams(baseParams, ui) {
  const { tamanoCeldaM, metodoHotspot, areaSelectionGeojson } = ui
  const params = {
    ...baseParams,
    metodo: metodoHotspot,
    tamano_celda_m: Number(tamanoCeldaM) || 300,
  }
  if (metodoHotspot === 'area' && areaSelectionGeojson) {
    params.geojson = areaSelectionGeojson
  }
  return params
}

export async function fetchMissingMapLayer(baseParams, bundle, ui) {
  const { viewMode, choroplethMetric, mapLimite, tamanoCeldaM, metodoHotspot, comunaId, barrioId } =
    ui
  const nivel =
    barrioId || comunaId ? 'barrio' : 'comuna'

  if (viewMode === 'cuadricula') {
    const hk = hotspotsCacheKey(
      tamanoCeldaM,
      metodoHotspot,
      ui.areaSelectionGeojson || '',
    )
    if (bundle.hotspots[hk]) return { hotspots: bundle.hotspots[hk] }
    const data = await fetchDashboardHotspotsCuadricula(hotspotsFetchParams(baseParams, ui))
    bundle.hotspots[hk] = data
    return { hotspots: data }
  }

  if (viewMode === 'detalle') {
    const limite = mapLimite === '0' ? 0 : Number(mapLimite) || DEFAULT_DETALLE_LIMITE
    const dk = detalleCacheKey(limite)
    if (bundle.detalle[dk]) return bundle.detalle[dk]
    const detalle = await fetchDashboardMapaDetalle({
      ...baseParams,
      nivel,
      metrica: choroplethMetric,
      limite,
    })
    bundle.detalle[dk] = {
      choropleth: detalle.choropleth,
      puntos: detalle.puntos,
      puntos_meta: detalle.puntos_meta,
    }
    return bundle.detalle[dk]
  }

  const ck = choroplethCacheKey(nivel, choroplethMetric)
  if (bundle.choropleth[ck]) return { choropleth: bundle.choropleth[ck] }
  const choropleth = await fetchDashboardChoroplethTerritorial({
    ...baseParams,
    nivel,
    metrica: choroplethMetric,
  })
  bundle.choropleth[ck] = choropleth
  return { choropleth }
}

/** Resuelve qué capas mostrar según el estado actual de la UI. */
export function pickViewFromBundle(bundle, ui) {
  const {
    viewMode,
    choroplethMetric,
    mapLimite,
    tamanoCeldaM,
    metodoHotspot,
    comunaId,
    barrioId,
    nivelDensidad,
  } = ui
  const nivel = barrioId || comunaId ? 'barrio' : 'comuna'

  let choroplethData = null
  let pointsData = null
  let hotspotsData = null

  if (viewMode === 'cuadricula') {
    hotspotsData =
      bundle.hotspots[
        hotspotsCacheKey(tamanoCeldaM, metodoHotspot, ui.areaSelectionGeojson || '')
      ] ?? null
  } else if (viewMode === 'detalle') {
    const limite = mapLimite === '0' ? 0 : Number(mapLimite) || DEFAULT_DETALLE_LIMITE
    const d = bundle.detalle[detalleCacheKey(limite)]
    if (d) {
      choroplethData = d.choropleth
      pointsData = { puntos: d.puntos, meta: d.puntos_meta }
    }
  } else {
    choroplethData = bundle.choropleth[choroplethCacheKey(nivel, choroplethMetric)] ?? null
  }

  const densidadData =
    bundle.densidad[nivelDensidad] ?? bundle.densidad.comuna ?? null
  const rankingData =
    bundle.ranking[String(tamanoCeldaM)] ?? bundle.ranking[300] ?? null

  return {
    choroplethData,
    pointsData,
    hotspotsData,
    calidadData: bundle.calidad,
    densidadData,
    rankingData,
  }
}

export function hasCachedViewLayer(bundle, ui) {
  if (!bundle) return false
  const { viewMode, choroplethMetric, mapLimite, tamanoCeldaM, metodoHotspot, comunaId, barrioId } =
    ui
  const nivel = barrioId || comunaId ? 'barrio' : 'comuna'
  if (viewMode === 'cuadricula') {
    if (metodoHotspot === 'area' && !ui.areaSelectionGeojson) return false
    return Boolean(
      bundle.hotspots[
        hotspotsCacheKey(tamanoCeldaM, metodoHotspot, ui.areaSelectionGeojson || '')
      ],
    )
  }
  if (viewMode === 'detalle') {
    const limite = mapLimite === '0' ? 0 : Number(mapLimite) || DEFAULT_DETALLE_LIMITE
    return Boolean(bundle.detalle[detalleCacheKey(limite)])
  }
  return Boolean(bundle.choropleth[choroplethCacheKey(nivel, choroplethMetric)])
}
