import { feature } from 'topojson-client'

function hasValidFeatures(fc) {
  if (!fc?.features?.length) return false
  const g0 = fc.features[0]?.geometry
  const coords = g0?.coordinates
  return Array.isArray(coords) && coords.length > 0
}

/**
 * Convierte respuesta coroplética (GeoJSON o TopoJSON) a FeatureCollection para Leaflet.
 */
export function decodeChoroplethPayload(data) {
  if (!data) return data
  if (data.type !== 'Topology') return data

  const objectName = data.meta?.topojson_object || 'territorios'
  const topoObject = data.objects?.[objectName]
  if (!topoObject) {
    return { type: 'FeatureCollection', features: [], meta: data.meta }
  }

  try {
    const decoded = feature(data, topoObject)
    const fc =
      decoded.type === 'FeatureCollection'
        ? decoded
        : decoded.type === 'Feature'
          ? { type: 'FeatureCollection', features: [decoded] }
          : null
    if (!fc || !hasValidFeatures(fc)) {
      return { type: 'FeatureCollection', features: [], meta: data.meta }
    }
    return { ...fc, meta: data.meta }
  } catch {
    return { type: 'FeatureCollection', features: [], meta: data.meta }
  }
}
