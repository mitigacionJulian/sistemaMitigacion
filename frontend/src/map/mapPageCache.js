/**
 * Caché en memoria para /mapa: metadatos de sesión + paquetes por combinación de filtros.
 */

/** @typedef {{
 *   filterKey: string
 *   desde: string
 *   hasta: string
 *   comunaId: string
 *   barrioId: string
 *   claseId: string
 *   modoTerritorio: string
 *   choropleth: Record<string, object>
 *   detalle: Record<string, { choropleth: object, puntos: object[], puntos_meta?: object }>
 *   hotspots: Record<string, object>
 *   calidad: object | null
 *   densidad: { comuna: object | null, barrio: object | null }
 *   ranking: Record<string, object | null>
 *   warmedAt: number
 * }} MapFilterBundle */

/** @type {{ rangoMeta: object | null, catalogos: object | null } | null} */
let sessionMeta = null

/** @type {Map<string, MapFilterBundle>} */
const bundles = new Map()

export function buildFilterKey(params) {
  const {
    desde,
    hasta,
    comunaId = '',
    barrioId = '',
    claseId = '',
    modoTerritorio = 'registro',
  } = params
  return [desde, hasta, comunaId, barrioId, claseId, modoTerritorio].join('|')
}

/** Clave de coropleta: nivel + métrica (ej. comuna_densidad). */
export function choroplethCacheKey(nivel, metrica) {
  return `${nivel}_${metrica}`
}

export function detalleCacheKey(limite) {
  return String(limite === '0' || limite === 0 ? 0 : limite)
}

/** Huella corta del polígono para claves de caché en modo área. */
export function geojsonCacheFingerprint(geojson) {
  if (!geojson) return ''
  let h = 0
  for (let i = 0; i < geojson.length; i += 1) {
    h = (Math.imul(31, h) + geojson.charCodeAt(i)) | 0
  }
  return Math.abs(h).toString(36)
}

export function hotspotsCacheKey(tamanoCeldaM, metodo, areaGeojson = '') {
  const fp = geojsonCacheFingerprint(areaGeojson)
  const mallaTag = metodo === 'area' ? '_malla2' : ''
  if (fp) return `${tamanoCeldaM}_${metodo}_${fp}${mallaTag}`
  return `${tamanoCeldaM}_${metodo}${mallaTag}`
}

export function createEmptyBundle(ctx) {
  return {
    filterKey: ctx.filterKey,
    desde: ctx.desde,
    hasta: ctx.hasta,
    comunaId: ctx.comunaId ?? '',
    barrioId: ctx.barrioId ?? '',
    claseId: ctx.claseId ?? '',
    modoTerritorio: ctx.modoTerritorio ?? 'registro',
    choropleth: {},
    detalle: {},
    hotspots: {},
    calidad: null,
    densidad: { comuna: null, barrio: null },
    ranking: { 300: null, 500: null },
    warmedAt: Date.now(),
  }
}

export function getSessionMeta() {
  return sessionMeta
}

/** @param {{ rangoMeta: object, catalogos: object }} meta */
export function setSessionMeta(meta) {
  sessionMeta = meta
}

/** @returns {MapFilterBundle | undefined} */
export function getMapBundle(filterKey) {
  return bundles.get(filterKey)
}

/** @param {MapFilterBundle} bundle */
export function setMapBundle(bundle) {
  bundles.set(bundle.filterKey, bundle)
}

export function listCachedFilterKeys() {
  return [...bundles.keys()]
}

/** Paquete precalentado: capas usadas en la UI sin peticiones extra. */
export function isBundleWarmComplete(bundle) {
  if (!bundle?.calidad) return false
  if (!bundle.densidad?.comuna || !bundle.densidad?.barrio) return false
  if (!bundle.ranking?.[300] || !bundle.ranking?.[500]) return false
  if (!bundle.hotspots?.[hotspotsCacheKey('300', 'cuadricula')]) return false
  if (!bundle.hotspots?.[hotspotsCacheKey('500', 'cuadricula')]) return false
  const niveles = ['comuna', 'barrio']
  const metricas = ['densidad', 'conteo']
  for (const n of niveles) {
    for (const m of metricas) {
      if (!bundle.choropleth?.[choroplethCacheKey(n, m)]) return false
    }
  }
  if (!bundle.detalle?.[detalleCacheKey(10000)]) return false
  return true
}

export function clearMapPageCache() {
  sessionMeta = null
  bundles.clear()
}
