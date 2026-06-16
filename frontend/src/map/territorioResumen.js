import { choroplethHasFeatures, decodeChoroplethPayload } from './choroplethDecode.js'

function featureTerritorioId(feature) {
  const p = feature?.properties || {}
  return String(p.id ?? p.territorio_id ?? '')
}

/**
 * Busca un feature por id en coropleta (GeoJSON o TopoJSON).
 * @param {object | null | undefined} choroplethData
 * @param {string | number} territoryId
 */
export function findTerritorioFeature(choroplethData, territoryId) {
  if (!choroplethData || territoryId === '' || territoryId == null) return null
  const fc = decodeChoroplethPayload(choroplethData)
  const tid = String(territoryId)
  return fc?.features?.find((f) => featureTerritorioId(f) === tid) ?? null
}

/**
 * @param {object} feature — GeoJSON Feature
 * @param {{ nivel: string, desde?: string, hasta?: string, metrica?: string }} ctx
 */
export function buildTerritorioResumenFromFeature(feature, ctx) {
  if (!feature) return null
  const p = feature.properties || {}
  const nombre = p.comuna_nombre ? `${p.nombre} (${p.comuna_nombre})` : p.nombre || 'Territorio'
  return {
    nivel: ctx.nivel,
    nombre,
    territorio_id: p.id ?? p.territorio_id,
    codigo: p.codigo || null,
    area_km2: p.area_km2,
    incidentes: p.incidentes,
    densidad_km2: p.densidad_km2,
    ratio_vs_ciudad: p.ratio_vs_ciudad ?? null,
    desde: ctx.desde,
    hasta: ctx.hasta,
    metrica: ctx.metrica,
    nota:
      'Superficie del polígono territorial (PostGIS ST_Area en geography). ' +
      'Incidentes y densidad respetan el periodo y filtros activos.',
  }
}

/**
 * Elige la capa coroplética adecuada según nivel y selección territorial.
 * @param {{
 *   choroplethData: object | null
 *   bundleLayer: object | null
 *   lookupChoroplethData: object | null
 *   nivel: string
 *   comunaId: string
 *   barrioId: string
 *   requireTerritoryMatch: boolean
 * }} params
 */
export function resolveChoroplethLayer({
  choroplethData,
  bundleLayer,
  lookupChoroplethData,
  nivel,
  comunaId,
  barrioId,
  requireTerritoryMatch,
}) {
  const candidates = [choroplethData, bundleLayer, lookupChoroplethData].filter(Boolean)

  const matches = (data, strictTerritory) => {
    if (!choroplethHasFeatures(data)) return false
    if (data.meta?.nivel && data.meta.nivel !== nivel) return false
    if (!strictTerritory) return true
    if (barrioId && !findTerritorioFeature(data, barrioId)) return false
    if (!barrioId && comunaId && !findTerritorioFeature(data, comunaId)) return false
    return true
  }

  if (requireTerritoryMatch) {
    for (const data of candidates) {
      if (matches(data, true)) return data
    }
  }

  for (const data of candidates) {
    if (matches(data, false)) return data
  }

  return null
}

/**
 * Resumen del territorio seleccionado en filtros (comuna y/o barrio).
 * @param {{
 *   comunaId: string
 *   barrioId: string
 *   choroplethData: object | null
 *   lookupChoroplethData: object | null
 *   desde: string
 *   hasta: string
 *   metrica: string
 * }} params
 */
export function resolveTerritorioResumen({
  comunaId,
  barrioId,
  choroplethData,
  lookupChoroplethData,
  desde,
  hasta,
  metrica,
}) {
  if (!comunaId && !barrioId) return null

  const ctx = { desde, hasta, metrica }

  if (barrioId) {
    let feature = findTerritorioFeature(choroplethData, barrioId)
    if (!feature && lookupChoroplethData) {
      feature = findTerritorioFeature(lookupChoroplethData, barrioId)
    }
    return buildTerritorioResumenFromFeature(feature, { ...ctx, nivel: 'barrio' })
  }

  let feature = null
  if (choroplethData?.meta?.nivel === 'comuna') {
    feature = findTerritorioFeature(choroplethData, comunaId)
  }
  if (!feature && lookupChoroplethData) {
    feature = findTerritorioFeature(lookupChoroplethData, comunaId)
  }

  return buildTerritorioResumenFromFeature(feature, { ...ctx, nivel: 'comuna' })
}
