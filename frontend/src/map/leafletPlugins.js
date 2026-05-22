/**
 * Plugins Leaflet (UMD) que esperan `L` en `window`.
 * Importar este módulo una vez antes de usar L.heatLayer / L.markerClusterGroup.
 */
import L from 'leaflet'

if (typeof window !== 'undefined') {
  window.L = L
}

import 'leaflet.heat/dist/leaflet-heat.js'
import 'leaflet.markercluster/dist/MarkerCluster.css'
import 'leaflet.markercluster/dist/MarkerCluster.Default.css'
import 'leaflet.markercluster/dist/leaflet.markercluster.js'

export { L }
