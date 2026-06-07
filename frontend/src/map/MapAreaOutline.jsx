import { useEffect } from 'react'
import { useMap } from 'react-leaflet'
import { L } from './leafletPlugins.js'
import { ensureHotspotsOutlinePane } from './mapHotspotPanes.js'

/**
 * Contorno del polígono dibujado (referencia visual sobre la cuadrícula recortada).
 * @param {{ geometryJson: string | null }} props
 */
export function MapAreaOutline({ geometryJson }) {
  const map = useMap()

  useEffect(() => {
    if (!geometryJson) return undefined
    let geometry
    try {
      geometry = JSON.parse(geometryJson)
    } catch {
      return undefined
    }
    const outlinePane = ensureHotspotsOutlinePane(map)
    const layer = L.geoJSON(
      { type: 'Feature', properties: {}, geometry },
      {
        pane: outlinePane,
        style: {
          color: '#0f766e',
          weight: 2.5,
          opacity: 0.95,
          fillOpacity: 0,
          dashArray: '7 5',
        },
        interactive: false,
      },
    )
    layer.addTo(map)
    return () => {
      map.removeLayer(layer)
    }
  }, [map, geometryJson])

  return null
}
