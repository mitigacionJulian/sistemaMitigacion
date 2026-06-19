import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'
import { MapContainer, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import { L } from '../map/leafletPlugins.js'
import {
  fetchDashboardBarrios,
  fetchDashboardCatalogos,
  fetchDashboardDensidadTerritorial,
  fetchDashboardChoroplethTerritorial,
  fetchDashboardHotspotsCuadricula,
  fetchDashboardHotspotsRanking,
  fetchDashboardMapaDetalle,
  fetchDashboardRangoFechas,
} from '../api/client.js'
import {
  buildFilterKey,
  choroplethCacheKey,
  createEmptyBundle,
  getMapBundle,
  getSessionMeta,
  isBundleWarmComplete,
  listCachedFilterKeys,
  setMapBundle,
  setSessionMeta,
} from '../map/mapPageCache.js'
import {
  fetchMissingMapLayer,
  hasCachedViewLayer,
  pickViewFromBundle,
  warmFilterBundle,
} from '../map/mapBundleLoader.js'
import { MapAreaAnalisisPanel } from '../map/MapAreaAnalisisPanel.jsx'
import { MapAreaOutline } from '../map/MapAreaOutline.jsx'
import { MapAreaSelection } from '../map/MapAreaSelection.jsx'
import {
  MapTerritorioResumenPanel,
  RATIO_VS_CIUDAD_HELP,
} from '../map/MapTerritorioResumenPanel.jsx'
import { choroplethHasFeatures } from '../map/choroplethDecode.js'
import {
  findTerritorioFeature,
  resolveChoroplethLayer,
  resolveTerritorioResumen,
} from '../map/territorioResumen.js'
import {
  ensureHotspotsGridPane,
  ensureHotspotsLabelPane,
  setHotspotPanesInteractive,
} from '../map/mapHotspotPanes.js'
import { LandingCalidadTerritorio } from './LandingCalidadTerritorio.jsx'
import { LandingGeoIndicators } from './LandingGeoIndicators.jsx'

const DEFAULT_CENTER = [6.2476, -75.5659]
const DEFAULT_ZOOM = 12
/** Por debajo de este zoom se muestra heatmap; arriba, puntos individuales (mismos datos). */
const DETAIL_POINTS_MIN_ZOOM = 14
const MARKER_BATCH_SIZE = 400

const FECHAS_REF_MEDE = {
  default_desde: '2021-01-01',
  default_hasta: '2021-09-30',
  selector_fecha_min: '2014-01-01',
  selector_fecha_max: '2021-09-30',
}

const MAP_LIMITE_OPTIONS = [
  { value: '5000', label: '5.000' },
  { value: '10000', label: '10.000 — recomendado' },
  { value: '20000', label: '20.000' },
  { value: '0', label: 'Sin tope (hasta 100.000)' },
]

const MAP_LIMITE_ALLOWED = new Set(MAP_LIMITE_OPTIONS.map((o) => o.value))
const DEFAULT_MAP_LIMITE = '10000'
const HOTSPOT_MAP_LABEL_MAX_RANK = 10
const HOTSPOT_CAPTURE_LABEL_MAX_RANK = 15
const HOTSPOT_RANK_LABEL_SIZE_PX = 22

const HOTSPOT_CELDA_OPTIONS = [
  { value: '300', label: '300 m — más detalle' },
  { value: '500', label: '500 m — más suave' },
]

const HOTSPOT_CELDA_AREA_M = '100'

const TERRITORIO_FILTRO_HELP = {
  registro:
    'Registro Mede: agrupa por comuna/barrio declarados en el dato original (comuna_id / barrio_id). ' +
    'Puede diferir del mapa si el texto del registro y la coordenada no coinciden.',
  espacial:
    'Polígono PostGIS: agrupa según el punto del incidente dentro del límite oficial ' +
    '(comuna_id_espacial / barrio_id_espacial). Solo cuenta incidentes con ubicación en el mapa.',
}

const INTENSIDAD_HELP = {
  densidad:
    'Densidad: colorea por incidentes ÷ km² del polígono. Normaliza por tamaño; útil para comparar ' +
    'concentración entre comunas o barrios.',
  conteo:
    'Número de incidentes: colorea por el conteo total en el periodo. Muestra volumen bruto; ' +
    'territorios grandes suelen destacar más aunque la concentración sea menor.',
}

const VIEW_MODES = [
  {
    id: 'territorio',
    label: 'Territorio',
    hint: 'Comunas o barrios coloreados por densidad (G01). Vista general del periodo.',
  },
  {
    id: 'detalle',
    label: 'Detalle',
    hint: 'Incidentes individuales sobre contorno territorial. Para calles y casos concretos.',
  },
  {
    id: 'cuadricula',
    label: 'Hotspots',
    hint: 'Cuadrícula P14 (300–500 m): focos locales que una comuna puede «promediar». Compare con Territorio.',
  },
]

const HOTSPOT_AREA_POLYGON_TIP =
  'Al seleccionar un polígono grande el sistema tardará más en cargar y guardar los datos en caché. ' +
  'Se recomienda dibujar áreas de aproximadamente 1 km de lado (≈1 km²) o menos.'

const CHOROPLETH_RGB_STOPS = [
  [0, [0, 0, 4]],
  [0.2, [66, 10, 104]],
  [0.4, [147, 38, 103]],
  [0.6, [221, 81, 58]],
  [0.8, [252, 165, 10]],
  [1, [252, 255, 164]],
]

function interpolateChoroplethRgb(t) {
  const x = Math.max(0, Math.min(1, t))
  for (let i = 1; i < CHOROPLETH_RGB_STOPS.length; i += 1) {
    const [t1, c1] = CHOROPLETH_RGB_STOPS[i - 1]
    const [t2, c2] = CHOROPLETH_RGB_STOPS[i]
    if (x <= t2) {
      const f = t2 > t1 ? (x - t1) / (t2 - t1) : 0
      return c1.map((v, j) => Math.round(v + (c2[j] - v) * f))
    }
  }
  return CHOROPLETH_RGB_STOPS[CHOROPLETH_RGB_STOPS.length - 1][1]
}

function choroplethStyle(value, minVal, maxVal, sinDatos, selected, fillOpacity = 0.9) {
  if (sinDatos || value == null || value <= 0) {
    return {
      fillColor: '#d1d5db',
      fillOpacity: 0.5,
      color: selected ? '#1d4ed8' : '#94a3b8',
      weight: selected ? 2.5 : 0.7,
    }
  }
  const span = maxVal - minVal
  const t = span > 0 ? (value - minVal) / span : 1
  const [r, g, b] = interpolateChoroplethRgb(t)
  return {
    fillColor: `rgb(${r},${g},${b})`,
    fillOpacity,
    color: selected ? '#1e3a8a' : '#334155',
    weight: selected ? 2.5 : 0.85,
  }
}

function resolveChoroplethNivel(viewMode, comunaId, barrioId) {
  if (barrioId) return 'barrio'
  if (viewMode === 'detalle' && comunaId) return 'barrio'
  return 'comuna'
}

function fmtChoroplethVal(v, metrica) {
  if (v == null || Number.isNaN(Number(v))) return '—'
  if (metrica === 'conteo') return Number(v).toLocaleString('es-CO')
  return Number(v).toLocaleString('es-CO', { maximumFractionDigits: 2 })
}

function fmtAreaKm2(v) {
  if (v == null || Number.isNaN(Number(v))) return '—'
  return Number(v).toLocaleString('es-CO', {
    minimumFractionDigits: 3,
    maximumFractionDigits: 3,
  })
}

function fmtNum(v, digits = 0) {
  if (v == null || Number.isNaN(Number(v))) return '—'
  return Number(v).toLocaleString('es-CO', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  })
}

function normalizeMapLimite(raw) {
  return MAP_LIMITE_ALLOWED.has(String(raw)) ? String(raw) : DEFAULT_MAP_LIMITE
}

function queryId(v) {
  if (v === '' || v === undefined || v === null) return undefined
  const n = Number(v)
  return Number.isFinite(n) ? n : undefined
}

function escapeHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function pctParticipacionArea(conteo, totalIncidentes) {
  const t = Number(totalIncidentes)
  const c = Number(conteo)
  if (!t || t <= 0 || !Number.isFinite(c) || c <= 0) return null
  return (c / t) * 100
}

function buildHotspotAreaCellTooltipHtml(p, totalIncidentes) {
  const conteo = Number(p.conteo || 0)
  const lead =
    '<p class="landing-map-tooltip-lead"><strong>Celda dentro del área seleccionada</strong></p>'
  if (conteo <= 0) {
    return `<div class="landing-map-tooltip">${lead}Sin incidentes en el periodo activo.</div>`
  }
  const pct = pctParticipacionArea(conteo, totalIncidentes)
  const pctLine =
    pct != null
      ? `<br/>Participación: <strong>${escapeHtml(fmtNum(pct, 1))} %</strong> del área`
      : ''
  return (
    `<div class="landing-map-tooltip">${lead}` +
    `Incidentes: <strong>${escapeHtml(conteo)}</strong>${pctLine}</div>`
  )
}

function buildHotspotCellPopupHtml(p, { areaSelection, totalIncidentes }) {
  const celdaId = p.celda_id || `C${String(p.rank || '').padStart(3, '0')}`
  if (areaSelection) {
    const conteo = Number(p.conteo || 0)
    if (conteo <= 0) {
      return (
        `<div class="landing-map-popup"><strong>Celda dentro del área seleccionada</strong><br/>` +
        `Sin incidentes en el periodo activo.</div>`
      )
    }
    const pct = pctParticipacionArea(conteo, totalIncidentes)
    const pctLine =
      pct != null
        ? `<br/>Participación: <strong>${escapeHtml(fmtNum(pct, 1))} %</strong> del total del área`
        : ''
    return (
      `<div class="landing-map-popup"><strong>Celda dentro del área seleccionada</strong><br/>` +
      `ID: <strong>${escapeHtml(celdaId)}</strong><br/>` +
      `Incidentes: <strong>${escapeHtml(conteo)}</strong>${pctLine}</div>`
    )
  }
  return (
    `<div class="landing-map-popup"><strong>Celda P14</strong><br/>` +
    `ID: <strong>${escapeHtml(celdaId)}</strong><br/>` +
    `Incidentes: <strong>${escapeHtml(p.conteo)}</strong><br/>` +
    `Densidad: <strong>${fmtChoroplethVal(p.densidad_por_km2, 'densidad')}</strong> / km²` +
    (p.recortada ? '<br/><em>Recortada al polígono</em>' : '') +
    `</div>`
  )
}

const VIEWPORT_COMPACT_PX = 900

function useViewportCompact() {
  const query = `(max-width: ${VIEWPORT_COMPACT_PX}px)`
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

function MapResizeEffects({ compact }) {
  const map = useMap()
  useEffect(() => {
    const id = requestAnimationFrame(() => map.invalidateSize())
    const delayed = window.setTimeout(() => map.invalidateSize(), 350)
    return () => {
      cancelAnimationFrame(id)
      window.clearTimeout(delayed)
    }
  }, [map, compact])
  useEffect(() => {
    const onResize = () => map.invalidateSize()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [map])
  return null
}

function MapFitBoundsOnce({ geojson, enabled }) {
  const map = useMap()
  const lastSig = useRef('')
  useEffect(() => {
    if (!enabled || !geojson?.features?.length) return
    const sig = String(geojson.meta?.fecha_inicio || '') + geojson.meta?.nivel + geojson.features.length
    if (sig === lastSig.current) return
    lastSig.current = sig
    try {
      const layer = L.geoJSON(geojson)
      const bounds = layer.getBounds()
      if (!bounds.isValid()) return
      const ne = bounds.getNorthEast()
      const sw = bounds.getSouthWest()
      const span = Math.max(Math.abs(ne.lat - sw.lat), Math.abs(ne.lng - sw.lng))
      if (span > 15) return
      map.fitBounds(bounds, { padding: [24, 24], maxZoom: 14 })
    } catch {
      /* ignore */
    }
  }, [map, geojson, enabled])
  return null
}

function ChoroplethLayer({ geojson, comunaId, barrioId, subdued = false }) {
  const map = useMap()
  useEffect(() => {
    if (!geojson?.features?.length) return undefined
    const meta = geojson.meta || {}
    const minV = Number(meta.valor_min ?? 0)
    const maxV = Number(meta.valor_max ?? 0)
    const selComuna = comunaId ? String(comunaId) : ''
    const selBarrio = barrioId ? String(barrioId) : ''
    const fillOpacity = subdued ? 0.28 : 0.9

    const layer = L.geoJSON(geojson, {
      style: (feature) => {
        const p = feature?.properties || {}
        const fid = String(p.id ?? p.territorio_id ?? '')
        const selected =
          (selBarrio && fid === selBarrio) ||
          (!selBarrio && selComuna && fid === selComuna && meta.nivel === 'comuna')
        return choroplethStyle(p.valor_coropletica, minV, maxV, p.sin_datos, selected, fillOpacity)
      },
      onEachFeature: (feature, leafletLayer) => {
        const p = feature?.properties || {}
        const titulo = p.comuna_nombre ? `${p.nombre} (${p.comuna_nombre})` : p.nombre || 'Territorio'
        const ratioLine =
          p.ratio_vs_ciudad != null && Number.isFinite(Number(p.ratio_vs_ciudad))
            ? `<br/>Ratio vs ciudad (G02): <strong>${fmtChoroplethVal(p.ratio_vs_ciudad, 'densidad')}</strong>×` +
              `<br/><span class="landing-map-popup-note">${escapeHtml(RATIO_VS_CIUDAD_HELP)}</span>`
            : ''
        leafletLayer.bindPopup(
          `<div class="landing-map-popup"><strong>${escapeHtml(titulo)}</strong><br/>` +
            `Superficie: <strong>${fmtAreaKm2(p.area_km2)}</strong> km²<br/>` +
            `Incidentes: <strong>${escapeHtml(p.incidentes)}</strong><br/>` +
            `Densidad: <strong>${fmtChoroplethVal(p.densidad_km2, 'densidad')}</strong> / km²` +
            ratioLine +
            `</div>`,
        )
      },
    })
    layer.addTo(map)
    return () => {
      map.removeLayer(layer)
    }
  }, [map, geojson, comunaId, barrioId, subdued])
  return null
}

function hotspotCellCenter(feature, leafletLayer) {
  try {
    if (leafletLayer?.getBounds?.()?.isValid?.()) {
      const center =
        typeof leafletLayer.getCenter === 'function'
          ? leafletLayer.getCenter()
          : leafletLayer.getBounds().getCenter()
      if (center && Number.isFinite(center.lat) && Number.isFinite(center.lng)) {
        return center
      }
    }
  } catch {
    /* fallback below */
  }

  const geom = feature?.geometry
  const ring =
    geom?.type === 'Polygon'
      ? geom.coordinates?.[0]
      : geom?.type === 'MultiPolygon'
        ? geom.coordinates?.[0]?.[0]
        : null
  if (!ring?.length) return null

  const n = ring.length > 1 ? ring.length - 1 : ring.length
  if (n <= 0) return null

  let lat = 0
  let lng = 0
  for (let i = 0; i < n; i += 1) {
    lng += Number(ring[i][0] || 0)
    lat += Number(ring[i][1] || 0)
  }
  return L.latLng(lat / n, lng / n)
}

function hotspotsMatchTerritoryFilter(hotspotsData, comunaId, barrioId) {
  const filtros = hotspotsData?.meta?.filtros
  if (!filtros) return !comunaId && !barrioId
  if (barrioId) {
    return filtros.barrio_id != null && String(filtros.barrio_id) === String(barrioId)
  }
  if (comunaId) {
    return filtros.comuna_id != null && String(filtros.comuna_id) === String(comunaId)
  }
  return filtros.comuna_id == null && filtros.barrio_id == null
}

function hotspotsMatchAreaSelection(hotspotsData, areaSelectionGeojson) {
  if (!areaSelectionGeojson || !hotspotsData?.meta) return false
  if (hotspotsData.meta.metodo !== 'area') return false
  return Boolean(hotspotsData.meta.filtro_geojson) && (hotspotsData.features?.length ?? 0) > 0
}

function createHotspotRankLabel(map, latlng, labelText) {
  const pane = ensureHotspotsLabelPane(map)
  const size = HOTSPOT_RANK_LABEL_SIZE_PX
  const half = size / 2
  return L.marker(latlng, {
    pane,
    interactive: false,
    keyboard: false,
    zIndexOffset: 1000,
    icon: L.divIcon({
      className: 'landing-map-cell-rank-marker',
      html: `<span class="landing-map-cell-rank-badge">${labelText}</span>`,
      iconSize: [size, size],
      iconAnchor: [half, half],
    }),
  })
}

function HotspotGridLayer({
  geojson,
  editorBlocksMap = false,
  areaSelectionActive = false,
  showCellIds = false,
  cellIdMaxRank = null,
  cellIdLabelMode = 'rank',
}) {
  const map = useMap()
  const rendererRef = useRef(null)

  useEffect(() => {
    setHotspotPanesInteractive(map, !editorBlocksMap)
    return () => setHotspotPanesInteractive(map, true)
  }, [map, editorBlocksMap])

  useEffect(() => {
    if (!geojson?.features?.length) return undefined

    let layer = null
    let rankLabels = null

    try {
      const mallaCompleta = Boolean(geojson.meta?.malla_completa)
      const totalIncidentes = Number(geojson.meta?.total_incidentes || 0)
      const maxD = Number(geojson.meta?.densidad_max_km2 || 0)
      const densities = geojson.features
        .map((f) => Number(f?.properties?.densidad_por_km2 || 0))
        .filter((d) => d > 0)
      const minD = densities.length ? Math.min(...densities) : 0
      const gridPane = ensureHotspotsGridPane(map)
      setHotspotPanesInteractive(map, !editorBlocksMap)

      if (!rendererRef.current) rendererRef.current = L.canvas({ pane: gridPane, padding: 0.35 })

      rankLabels = L.layerGroup()

      layer = L.geoJSON(geojson, {
      pane: gridPane,
      renderer: rendererRef.current,
      interactive: true,
      style: (feature) => {
        const conteo = Number(feature?.properties?.conteo || 0)
        const d = Number(feature?.properties?.densidad_por_km2 || 0)
        if (mallaCompleta && conteo <= 0) {
          return {
            fillColor: '#cbd5e1',
            fillOpacity: 0.72,
            color: '#64748b',
            weight: 0.85,
            interactive: true,
          }
        }
        return { ...choroplethStyle(d, minD, maxD, d <= 0, false, 0.82), interactive: true }
      },
      onEachFeature: (feature, leafletLayer) => {
        const p = feature?.properties || {}
        const popupOpts = { areaSelection: areaSelectionActive, totalIncidentes }
        const popupHtml = buildHotspotCellPopupHtml(p, popupOpts)
        const celdaId = p.celda_id || `C${String(p.rank || '').padStart(3, '0')}`
        leafletLayer.bindPopup(popupHtml, {
          className: 'landing-map-leaflet-popup',
          maxWidth: 280,
        })

        const rank = Number(p.rank || 0)
        const conteo = Number(p.conteo || 0)
        const withinRankLimit =
          cellIdMaxRank == null || (rank > 0 && rank <= cellIdMaxRank)
        const showRankOnCell = showCellIds && withinRankLimit && rank > 0 && conteo > 0
        if (showRankOnCell) {
          const useRankLabel = cellIdLabelMode === 'rank'
          const labelText = useRankLabel ? String(rank) : String(celdaId)
          if (useRankLabel) {
            const center = hotspotCellCenter(feature, leafletLayer)
            if (center) {
              rankLabels.addLayer(createHotspotRankLabel(map, center, labelText))
            }
          } else {
            leafletLayer.bindTooltip(labelText, {
              permanent: true,
              direction: 'center',
              className: 'landing-map-cell-id-tooltip',
              opacity: 0.98,
              interactive: false,
            })
          }
        }

        if (areaSelectionActive && !showRankOnCell) {
          leafletLayer.bindTooltip(buildHotspotAreaCellTooltipHtml(p, totalIncidentes), {
            sticky: true,
            direction: 'top',
            className: 'landing-map-leaflet-tooltip',
            opacity: 0.96,
            interactive: true,
          })
          leafletLayer.on('mouseover', function onCellOver() {
            this.openTooltip()
          })
          leafletLayer.on('mouseout', function onCellOut() {
            this.closeTooltip()
          })
        }

        leafletLayer.on('click', function onCellClick(e) {
          L.DomEvent.stopPropagation(e)
          this.openPopup(e.latlng)
        })
      },
    })
      layer.bringToFront()
      layer.addTo(map)
      rankLabels.addTo(map)
    } catch (error) {
      console.error('HotspotGridLayer: no se pudo dibujar la cuadrícula', error)
      return undefined
    }

    return () => {
      if (layer) map.removeLayer(layer)
      if (rankLabels) map.removeLayer(rankLabels)
    }
  }, [map, geojson, areaSelectionActive, editorBlocksMap, showCellIds, cellIdMaxRank, cellIdLabelMode])
  return null
}

function MapZoomTracker({ onZoom }) {
  const map = useMap()
  useEffect(() => {
    onZoom(map.getZoom())
  }, [map, onZoom])
  useMapEvents({
    zoomend: () => onZoom(map.getZoom()),
  })
  return null
}

function MapFlyTo({ focus }) {
  const map = useMap()
  useEffect(() => {
    if (focus?.lat == null || focus?.lon == null) return undefined
    map.flyTo([focus.lat, focus.lon], focus.zoom ?? 15, { duration: 0.75 })
    return undefined
  }, [focus, map])
  return null
}

function buildHeatLayerData(puntos) {
  if (!puntos?.length) return []
  const grid = new Map()
  for (let i = 0; i < puntos.length; i += 1) {
    const p = puntos[i]
    const latK = Math.round(p.latitud * 9000)
    const lngK = Math.round(p.longitud * 9000)
    const key = `${latK}:${lngK}`
    grid.set(key, (grid.get(key) || 0) + 1)
  }
  let maxCount = 1
  for (const count of grid.values()) {
    if (count > maxCount) maxCount = count
  }
  const data = []
  for (const [key, count] of grid) {
    const [latK, lngK] = key.split(':').map(Number)
    const t = Math.sqrt(count / maxCount)
    data.push([latK / 9000, lngK / 9000, 0.12 + t * 0.88])
  }
  return data
}

function DetailPointsLayer({ puntos, showHeat, showMarkers, mapZoom }) {
  const map = useMap()
  const heatRef = useRef(null)
  const groupRef = useRef(null)
  const buildGenRef = useRef(0)

  useEffect(() => {
    const gen = buildGenRef.current + 1
    buildGenRef.current = gen
    let cancelled = false

    if (groupRef.current) {
      map.removeLayer(groupRef.current)
      groupRef.current = null
    }

    if (!puntos?.length) return undefined

    const group = L.layerGroup()
    groupRef.current = group
    const renderer = L.canvas({ padding: 0.5 })
    let idx = 0

    const step = () => {
      if (cancelled || buildGenRef.current !== gen) return
      const end = Math.min(idx + MARKER_BATCH_SIZE, puntos.length)
      while (idx < end) {
        const p = puntos[idx]
        idx += 1
        const marker = L.circleMarker([p.latitud, p.longitud], {
          radius: 4,
          renderer,
          fillColor: '#0f766e',
          fillOpacity: 0.65,
          color: '#ffffff',
          weight: 1,
          opacity: 0.85,
        })
        marker.on('click', () => {
          if (!marker.getPopup()) {
            marker.bindPopup(
              `<div class="landing-map-popup"><strong>${escapeHtml(p.radicado ?? '')}</strong><br/>` +
                `${escapeHtml(p.fecha_incidente ?? '')}<br/>${escapeHtml(p.clase_incidente || '—')}</div>`,
            )
          }
          marker.openPopup()
        })
        group.addLayer(marker)
      }
      if (idx < puntos.length) {
        requestAnimationFrame(step)
      }
    }
    requestAnimationFrame(step)

    return () => {
      cancelled = true
      if (groupRef.current) {
        map.removeLayer(groupRef.current)
        groupRef.current = null
      }
    }
  }, [map, puntos])

  useEffect(() => {
    if (heatRef.current) {
      map.removeLayer(heatRef.current)
      heatRef.current = null
    }
    if (!puntos?.length || typeof L.heatLayer !== 'function') return undefined

    const radius = Math.max(11, 22 - mapZoom * 0.9)
    const blur = Math.max(7, 14 - mapZoom * 0.45)
    heatRef.current = L.heatLayer(buildHeatLayerData(puntos), {
      radius,
      blur,
      maxZoom: DETAIL_POINTS_MIN_ZOOM,
      minOpacity: 0.4,
      max: 1.0,
      gradient: {
        0.1: '#134e4a',
        0.35: '#0f766e',
        0.55: '#ca8a04',
        0.75: '#ea580c',
        1.0: '#b91c1c',
      },
    })
    if (showHeat) heatRef.current.addTo(map)

    return () => {
      if (heatRef.current) {
        map.removeLayer(heatRef.current)
        heatRef.current = null
      }
    }
  }, [map, puntos, mapZoom, showHeat])

  useEffect(() => {
    const heat = heatRef.current
    const group = groupRef.current
    if (heat) {
      if (showHeat) heat.addTo(map)
      else map.removeLayer(heat)
    }
    if (group) {
      if (showMarkers) group.addTo(map)
      else map.removeLayer(group)
    }
  }, [map, showHeat, showMarkers, puntos])

  return null
}

export function LandingIncidentMap({
  variant = 'embedded',
  onReportContextChange,
  forceShowHotspotCellIds = false,
}) {
  const isPage = variant === 'page'
  const compact = useViewportCompact()

  const [rangoMeta, setRangoMeta] = useState(null)
  const [catalogos, setCatalogos] = useState({ comunas: [], clases_incidente: [] })
  const [barrios, setBarrios] = useState([])

  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [comunaId, setComunaId] = useState('')
  const [barrioId, setBarrioId] = useState('')
  const [claseId, setClaseId] = useState('')
  const [modoTerritorio, setModoTerritorio] = useState('registro')
  const [viewMode, setViewMode] = useState('territorio')
  const [choroplethMetric, setChoroplethMetric] = useState('densidad')
  const [mapLimite, setMapLimite] = useState(DEFAULT_MAP_LIMITE)
  const [tamanoCeldaM, setTamanoCeldaM] = useState('300')
  const [metodoHotspot, setMetodoHotspot] = useState('cuadricula')
  const [areaSelectionGeojson, setAreaSelectionGeojson] = useState(null)
  const [areaEditorPhase, setAreaEditorPhase] = useState('inactive')
  const [showAdvanced, setShowAdvanced] = useState(false)

  const [choroplethData, setChoroplethData] = useState(null)
  const [territorioLookupChoropleth, setTerritorioLookupChoropleth] = useState(null)
  const [territorioLookupLoading, setTerritorioLookupLoading] = useState(false)
  const [pointsData, setPointsData] = useState(null)
  const [hotspotsData, setHotspotsData] = useState(null)
  const [err, setErr] = useState(null)
  const [initOk, setInitOk] = useState(!isPage)
  const [loadingBase, setLoadingBase] = useState(false)
  const [loadingOverlay, setLoadingOverlay] = useState(false)
  const [pageBlocking, setPageBlocking] = useState(isPage)
  const [pageBlockingMsg, setPageBlockingMsg] = useState('Preparando mapa e indicadores…')
  const [loadProgress, setLoadProgress] = useState(0)
  const [cacheRevision, setCacheRevision] = useState(0)
  const [calidadData, setCalidadData] = useState(null)
  const [densidadData, setDensidadData] = useState(null)
  const [rankingData, setRankingData] = useState(null)
  const [indicatorsLoading, setIndicatorsLoading] = useState(false)
  const [indicatorsErr, setIndicatorsErr] = useState(null)
  const [nivelDensidad, setNivelDensidad] = useState('comuna')
  const [mapZoom, setMapZoom] = useState(DEFAULT_ZOOM)
  const [mapFocus, setMapFocus] = useState(null)

  const loadGenRef = useRef(0)
  const areaSelectionRef = useRef(null)
  const areaReloadRef = useRef(null)
  const areaDismissedForGeojsonRef = useRef(null)
  const handleMapZoom = useCallback((z) => setMapZoom(z), [])
  const focusCellOnMap = useCallback((lat, lon) => {
    if (lat == null || lon == null) return
    setViewMode('cuadricula')
    setMapFocus({ lat: Number(lat), lon: Number(lon), zoom: 15, ts: Date.now() })
    const shellId = isPage ? 'map-page-shell' : 'landing-map-shell'
    document.getElementById(shellId)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [isPage])

  useEffect(() => {
    setMapFocus(null)
  }, [desde, hasta, comunaId, barrioId, claseId, modoTerritorio, tamanoCeldaM, metodoHotspot, areaSelectionGeojson])

  const showPointMarkers = mapZoom >= DETAIL_POINTS_MIN_ZOOM
  const showHeatLayer = mapZoom < DETAIL_POINTS_MIN_ZOOM

  const selMin = rangoMeta?.selector_fecha_min ?? FECHAS_REF_MEDE.selector_fecha_min
  const selMax = rangoMeta?.selector_fecha_max ?? FECHAS_REF_MEDE.selector_fecha_max

  const buildBaseParams = useCallback(
    (desdeOverride, hastaOverride) => {
      const comunaQ = queryId(comunaId)
      const barrioQ = queryId(barrioId)
      const claseQ = queryId(claseId)
      return {
        desde: desdeOverride ?? desde,
        hasta: hastaOverride ?? hasta,
        ...(comunaQ !== undefined ? { comuna_id: comunaQ } : {}),
        ...(barrioQ !== undefined ? { barrio_id: barrioQ } : {}),
        ...(claseQ !== undefined ? { clase_incidente_id: claseQ } : {}),
        ...(modoTerritorio === 'espacial' ? { territorio: 'espacial' } : {}),
      }
    },
    [desde, hasta, comunaId, barrioId, claseId, modoTerritorio],
  )

  const uiViewState = useMemo(
    () => ({
      viewMode,
      choroplethMetric,
      mapLimite,
      tamanoCeldaM,
      metodoHotspot,
      areaSelectionGeojson,
      comunaId,
      barrioId,
      nivelDensidad,
    }),
    [
      viewMode,
      choroplethMetric,
      mapLimite,
      tamanoCeldaM,
      metodoHotspot,
      areaSelectionGeojson,
      comunaId,
      barrioId,
      nivelDensidad,
    ],
  )

  const handleAreaSelectionChange = useCallback((geom) => {
    setAreaSelectionGeojson(geom)
  }, [])

  const handleAreaEditorPhaseChange = useCallback((phase) => {
    setAreaEditorPhase(phase)
    if (phase === 'draw') {
      areaDismissedForGeojsonRef.current = null
    }
  }, [])

  const areaEditorBlocksMap = areaEditorPhase === 'draw' || areaEditorPhase === 'adjust'

  const handleClearAreaSelection = useCallback(() => {
    areaSelectionRef.current?.clear()
    areaReloadRef.current = null
    areaDismissedForGeojsonRef.current = null
    setAreaEditorPhase('inactive')
    setAreaSelectionGeojson(null)
    setHotspotsData(null)
  }, [])

  const handleRedrawArea = useCallback(() => {
    areaDismissedForGeojsonRef.current = null
    areaReloadRef.current = null
    setHotspotsData(null)
    setAreaEditorPhase('draw')
    window.setTimeout(() => areaSelectionRef.current?.reactivate?.(), 50)
  }, [])

  const applyBundleToState = useCallback(
    (bundle) => {
      const view = pickViewFromBundle(bundle, uiViewState)
      setChoroplethData(view.choroplethData)
      setPointsData(view.pointsData)
      setHotspotsData(view.hotspotsData)
      setCalidadData(view.calidadData)
      setDensidadData(view.densidadData)
      setRankingData(view.rankingData)
    },
    [uiViewState],
  )

  const ensureFilterBundleData = useCallback(
    async ({ forceRefresh = false, showBlocking = true, fechaDesde, fechaHasta } = {}) => {
      const d = fechaDesde ?? desde
      const h = fechaHasta ?? hasta
      if (!d || !h) return null

      const fk = buildFilterKey({
        desde: d,
        hasta: h,
        comunaId,
        barrioId,
        claseId,
        modoTerritorio,
      })

      let bundle = getMapBundle(fk)
      if (!forceRefresh && bundle && isBundleWarmComplete(bundle)) {
        applyBundleToState(bundle)
        setLoadProgress(100)
        setPageBlockingMsg('Datos en caché')
        if (showBlocking) setPageBlocking(false)
        setInitOk(true)
        setCacheRevision((n) => n + 1)
        return bundle
      }

      if (showBlocking) {
        setPageBlocking(true)
        setLoadProgress(0)
        setPageBlockingMsg('Iniciando precarga…')
      }
      setIndicatorsErr(null)

      try {
        let meta = getSessionMeta()
        if (!meta?.rangoMeta) {
          setPageBlockingMsg('Consultando periodo y catálogos…')
          const [rango, cats] = await Promise.all([
            fetchDashboardRangoFechas().catch(() => ({ ...FECHAS_REF_MEDE, hay_datos: false })),
            fetchDashboardCatalogos().catch(() => ({ comunas: [], clases_incidente: [] })),
          ])
          meta = { rangoMeta: rango, catalogos: cats }
          setSessionMeta(meta)
          setRangoMeta(rango)
          setCatalogos(cats)
        }

        const baseParams = buildBaseParams(d, h)
        bundle = createEmptyBundle({
          filterKey: fk,
          desde: d,
          hasta: h,
          comunaId,
          barrioId,
          claseId,
          modoTerritorio,
        })

        await warmFilterBundle(baseParams, bundle, {
          onProgress: ({ percent, label }) => {
            setLoadProgress(percent)
            setPageBlockingMsg(label)
          },
        })

        setMapBundle(bundle)
        setCacheRevision((n) => n + 1)
        if (fechaDesde) setDesde(fechaDesde)
        if (fechaHasta) setHasta(fechaHasta)
        applyBundleToState(bundle)
        setErr(null)
        setInitOk(true)
        return bundle
      } catch (e) {
        const msg = e instanceof Error ? e.message : 'No se pudo cargar el mapa'
        setErr(msg)
        setIndicatorsErr(msg)
        return null
      } finally {
        if (showBlocking) setPageBlocking(false)
      }
    },
    [
      desde,
      hasta,
      comunaId,
      barrioId,
      claseId,
      modoTerritorio,
      buildBaseParams,
      applyBundleToState,
    ],
  )

  const handleNivelDensidadChange = useCallback(
    (nivel) => {
      setNivelDensidad(nivel)
      if (!isPage || !desde || !hasta || pageBlocking) return
      const fk = buildFilterKey({ desde, hasta, comunaId, barrioId, claseId, modoTerritorio })
      const bundle = getMapBundle(fk)
      if (bundle?.densidad?.[nivel]) {
        setDensidadData(bundle.densidad[nivel])
        return
      }
      void (async () => {
        setIndicatorsLoading(true)
        setIndicatorsErr(null)
        try {
          const dens = await fetchDashboardDensidadTerritorial({
            ...buildBaseParams(),
            tamano_celda_m: Number(tamanoCeldaM) || 300,
            nivel,
            limite: 12,
          })
          if (bundle) {
            bundle.densidad[nivel] = dens
            setMapBundle(bundle)
          }
          setDensidadData(dens)
        } catch (e) {
          setIndicatorsErr(
            e instanceof Error ? e.message : 'No se pudo actualizar densidad territorial',
          )
        } finally {
          setIndicatorsLoading(false)
        }
      })()
    },
    [
      isPage,
      desde,
      hasta,
      pageBlocking,
      buildBaseParams,
      tamanoCeldaM,
      comunaId,
      barrioId,
      claseId,
      modoTerritorio,
    ],
  )

  const loadMap = useCallback(async () => {
    if (!desde || !hasta) return

    if (isPage) {
      const fk = buildFilterKey({ desde, hasta, comunaId, barrioId, claseId, modoTerritorio })
      let bundle = getMapBundle(fk)
      if (!bundle || !isBundleWarmComplete(bundle)) {
        bundle = await ensureFilterBundleData({ forceRefresh: false, showBlocking: true })
      }
      if (!bundle) return

      if (hasCachedViewLayer(bundle, uiViewState)) {
        applyBundleToState(bundle)
        return
      }

      setPageBlocking(true)
      setLoadProgress(0)
      setPageBlockingMsg('Cargando capa adicional…')
      try {
        await fetchMissingMapLayer(buildBaseParams(), bundle, uiViewState)
        setMapBundle(bundle)
        applyBundleToState(bundle)
      } catch (e) {
        setErr(e instanceof Error ? e.message : 'No se pudo cargar la capa')
      } finally {
        setPageBlocking(false)
      }
      return
    }

    const gen = loadGenRef.current + 1
    loadGenRef.current = gen
    setErr(null)
    setLoadingBase(true)
    setLoadingOverlay(viewMode !== 'territorio')

    const baseParams = buildBaseParams()
    const nivel = resolveChoroplethNivel(viewMode, comunaId, barrioId)
    const choroplethParams = { ...baseParams, nivel, metrica: choroplethMetric }

    try {
      if (viewMode === 'cuadricula') {
        const hotspotParams = {
          ...baseParams,
          metodo: metodoHotspot,
          tamano_celda_m: Number(tamanoCeldaM) || 300,
        }
        if (metodoHotspot === 'area' && areaSelectionGeojson) {
          hotspotParams.geojson = areaSelectionGeojson
        }
        const hotspots = await fetchDashboardHotspotsCuadricula(hotspotParams)
        if (loadGenRef.current !== gen) return
        setChoroplethData(null)
        setPointsData(null)
        setHotspotsData(hotspots)
        return
      }

      if (viewMode === 'detalle') {
        const limite = mapLimite === '0' ? 0 : Number(mapLimite) || Number(DEFAULT_MAP_LIMITE)
        const detalle = await fetchDashboardMapaDetalle({
          ...choroplethParams,
          limite,
        })
        if (loadGenRef.current !== gen) return
        setChoroplethData(detalle.choropleth)
        setPointsData({ meta: detalle.puntos_meta, puntos: detalle.puntos })
        setHotspotsData(null)
        return
      }

      const choropleth = await fetchDashboardChoroplethTerritorial(choroplethParams)
      if (loadGenRef.current !== gen) return
      setChoroplethData(choropleth)
      setPointsData(null)
      setHotspotsData(null)
    } catch (e) {
      if (loadGenRef.current !== gen) return
      setErr(e instanceof Error ? e.message : 'No se pudo cargar el mapa')
      setChoroplethData(null)
      setPointsData(null)
      setHotspotsData(null)
    } finally {
      if (loadGenRef.current === gen) {
        setLoadingBase(false)
        setLoadingOverlay(false)
      }
    }
  }, [
    desde,
    hasta,
    buildBaseParams,
    comunaId,
    barrioId,
    claseId,
    modoTerritorio,
    viewMode,
    mapLimite,
    choroplethMetric,
    tamanoCeldaM,
    metodoHotspot,
    areaSelectionGeojson,
    isPage,
    ensureFilterBundleData,
    applyBundleToState,
    uiViewState,
  ])

  useEffect(() => {
    if (!mapFocus || viewMode !== 'cuadricula' || !desde || !hasta) return
    void loadMap()
  }, [mapFocus?.ts, viewMode, desde, hasta, loadMap])

  useEffect(() => {
    if (
      viewMode !== 'cuadricula' ||
      metodoHotspot !== 'area' ||
      !areaSelectionGeojson ||
      !desde ||
      !hasta
    ) {
      return undefined
    }
    if (areaReloadRef.current === areaSelectionGeojson) return undefined
    areaReloadRef.current = areaSelectionGeojson
    if (isPage) void ensureFilterBundleData({ forceRefresh: false, showBlocking: false })
    else void loadMap()
    return undefined
  }, [
    areaSelectionGeojson,
    viewMode,
    metodoHotspot,
    desde,
    hasta,
    isPage,
    loadMap,
    ensureFilterBundleData,
  ])

  useEffect(() => {
    if (viewMode !== 'cuadricula' || metodoHotspot !== 'area') return undefined
    if (!hotspotsData?.features?.length || !areaSelectionGeojson) return undefined
    if (areaDismissedForGeojsonRef.current === areaSelectionGeojson) return undefined
    areaDismissedForGeojsonRef.current = areaSelectionGeojson
    areaSelectionRef.current?.dismissEditor?.()
    setAreaEditorPhase('inactive')
    return undefined
  }, [hotspotsData, areaSelectionGeojson, viewMode, metodoHotspot])

  const pageInitRef = useRef(false)
  useEffect(() => {
    if (!isPage || pageInitRef.current) return undefined
    pageInitRef.current = true
    void (async () => {
      const meta = getSessionMeta()
      let d = desde
      let h = hasta
      if (!meta?.rangoMeta) {
        const [rango, cats] = await Promise.all([
          fetchDashboardRangoFechas().catch(() => ({ ...FECHAS_REF_MEDE, hay_datos: false })),
          fetchDashboardCatalogos().catch(() => ({ comunas: [], clases_incidente: [] })),
        ])
        setSessionMeta({ rangoMeta: rango, catalogos: cats })
        setRangoMeta(rango)
        setCatalogos(cats)
        d = rango.default_desde || FECHAS_REF_MEDE.default_desde
        h = rango.default_hasta || FECHAS_REF_MEDE.default_hasta
        setDesde(d)
        setHasta(h)
      } else {
        setRangoMeta(meta.rangoMeta)
        setCatalogos(meta.catalogos)
        if (!d) d = meta.rangoMeta?.default_desde || FECHAS_REF_MEDE.default_desde
        if (!h) h = meta.rangoMeta?.default_hasta || FECHAS_REF_MEDE.default_hasta
        setDesde(d)
        setHasta(h)
      }
      await ensureFilterBundleData({ showBlocking: true, fechaDesde: d, fechaHasta: h })
    })()
    return undefined
  }, [isPage, ensureFilterBundleData])

  useEffect(() => {
    if (!isPage || !initOk || pageBlocking || !desde || !hasta) return undefined
    const fk = buildFilterKey({ desde, hasta, comunaId, barrioId, claseId, modoTerritorio })
    const bundle = getMapBundle(fk)
    if (!bundle || !isBundleWarmComplete(bundle)) return undefined
    if (hasCachedViewLayer(bundle, uiViewState)) {
      applyBundleToState(bundle)
      return undefined
    }
    void (async () => {
      setPageBlocking(true)
      setLoadProgress(0)
      try {
        await fetchMissingMapLayer(buildBaseParams(), bundle, uiViewState)
        setMapBundle(bundle)
        applyBundleToState(bundle)
      } catch (e) {
        setErr(e instanceof Error ? e.message : 'No se pudo cambiar la vista')
      } finally {
        setPageBlocking(false)
      }
    })()
    return undefined
  }, [
    isPage,
    initOk,
    pageBlocking,
    desde,
    hasta,
    uiViewState,
    buildBaseParams,
    applyBundleToState,
    comunaId,
    barrioId,
    claseId,
    modoTerritorio,
  ])

  useEffect(() => {
    if (isPage) return undefined
    let alive = true
    ;(async () => {
      try {
        const [rango, cats] = await Promise.all([
          fetchDashboardRangoFechas().catch(() => ({ ...FECHAS_REF_MEDE, hay_datos: false })),
          fetchDashboardCatalogos().catch(() => ({ comunas: [], clases_incidente: [] })),
        ])
        if (!alive) return
        setRangoMeta(rango)
        setCatalogos(cats)
        const d = rango.default_desde
        const h = rango.default_hasta
        setDesde(d)
        setHasta(h)

        const choropleth = await fetchDashboardChoroplethTerritorial({
          desde: d,
          hasta: h,
          nivel: 'comuna',
          metrica: 'densidad',
        })
        if (!alive) return
        setChoroplethData(choropleth)
      } catch (e) {
        if (!alive) return
        setErr(e instanceof Error ? e.message : 'No se pudo cargar el mapa')
      } finally {
        if (alive) setInitOk(true)
      }
    })()
    return () => {
      alive = false
    }
  }, [isPage])

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
    if ((!comunaId && !barrioId) || !desde || !hasta) {
      setTerritorioLookupChoropleth(null)
      setTerritorioLookupLoading(false)
      return undefined
    }

    const targetId = barrioId || comunaId
    const lookupNivel = barrioId ? 'barrio' : 'comuna'

    if (choroplethHasFeatures(choroplethData) && findTerritorioFeature(choroplethData, targetId)) {
      setTerritorioLookupChoropleth(null)
      setTerritorioLookupLoading(false)
      return undefined
    }

    const fk = buildFilterKey({ desde, hasta, comunaId, barrioId, claseId, modoTerritorio })
    const bundle = getMapBundle(fk)
    const cached = bundle?.choropleth?.[choroplethCacheKey(lookupNivel, choroplethMetric)]
    if (cached && findTerritorioFeature(cached, targetId)) {
      setTerritorioLookupChoropleth(cached)
      setTerritorioLookupLoading(false)
      return undefined
    }

    let cancelled = false
    setTerritorioLookupLoading(true)
    void fetchDashboardChoroplethTerritorial({
      ...buildBaseParams(),
      nivel: lookupNivel,
      metrica: choroplethMetric,
    })
      .then((data) => {
        if (!cancelled) setTerritorioLookupChoropleth(data)
      })
      .catch(() => {
        if (!cancelled) setTerritorioLookupChoropleth(null)
      })
      .finally(() => {
        if (!cancelled) setTerritorioLookupLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [
    comunaId,
    barrioId,
    choroplethData,
    desde,
    hasta,
    claseId,
    modoTerritorio,
    choroplethMetric,
    cacheRevision,
    buildBaseParams,
  ])

  const puntos = useMemo(() => pointsData?.puntos ?? [], [pointsData])
  const pointsMeta = pointsData?.meta

  const currentFilterKey = useMemo(
    () =>
      desde && hasta
        ? buildFilterKey({ desde, hasta, comunaId, barrioId, claseId, modoTerritorio })
        : '',
    [desde, hasta, comunaId, barrioId, claseId, modoTerritorio, cacheRevision],
  )

  const filtersCached = useMemo(() => {
    if (!currentFilterKey) return false
    const bundle = getMapBundle(currentFilterKey)
    return Boolean(bundle && isBundleWarmComplete(bundle))
  }, [currentFilterKey, cacheRevision])

  const choroplethNivel = useMemo(
    () => resolveChoroplethNivel(viewMode, comunaId, barrioId),
    [viewMode, comunaId, barrioId],
  )

  const bundleChoroplethLayer = useMemo(() => {
    if (!currentFilterKey) return null
    const bundle = getMapBundle(currentFilterKey)
    return bundle?.choropleth?.[choroplethCacheKey(choroplethNivel, choroplethMetric)] ?? null
  }, [currentFilterKey, choroplethNivel, choroplethMetric, cacheRevision])

  const activeChoroplethData = useMemo(
    () =>
      resolveChoroplethLayer({
        choroplethData,
        bundleLayer: bundleChoroplethLayer,
        lookupChoroplethData: territorioLookupChoropleth,
        nivel: choroplethNivel,
        comunaId,
        barrioId,
        requireTerritoryMatch: Boolean(barrioId),
      }),
    [
      choroplethData,
      bundleChoroplethLayer,
      territorioLookupChoropleth,
      choroplethNivel,
      comunaId,
      barrioId,
    ],
  )

  const choroplethForResumen = useMemo(
    () =>
      resolveChoroplethLayer({
        choroplethData,
        bundleLayer: bundleChoroplethLayer,
        lookupChoroplethData: territorioLookupChoropleth,
        nivel: choroplethNivel,
        comunaId,
        barrioId,
        requireTerritoryMatch: Boolean(comunaId || barrioId),
      }),
    [
      choroplethData,
      bundleChoroplethLayer,
      territorioLookupChoropleth,
      choroplethNivel,
      comunaId,
      barrioId,
    ],
  )

  const comunaFallbackChoropleth = useMemo(() => {
    if (!barrioId || activeChoroplethData || !comunaId) return null
    const bundle = currentFilterKey ? getMapBundle(currentFilterKey) : null
    return resolveChoroplethLayer({
      choroplethData,
      bundleLayer: bundle?.choropleth?.[choroplethCacheKey('comuna', choroplethMetric)] ?? null,
      lookupChoroplethData: null,
      nivel: 'comuna',
      comunaId,
      barrioId: '',
      requireTerritoryMatch: true,
    })
  }, [
    barrioId,
    activeChoroplethData,
    comunaId,
    choroplethData,
    currentFilterKey,
    choroplethMetric,
    cacheRevision,
  ])

  const mapChoroplethData = activeChoroplethData ?? comunaFallbackChoropleth
  const barrioSinPoligono = Boolean(barrioId && !activeChoroplethData && comunaFallbackChoropleth)

  const choroplethMeta = mapChoroplethData?.meta
  const hasChoropleth = choroplethHasFeatures(mapChoroplethData)
  const hasHotspots = (hotspotsData?.features?.length ?? 0) > 0
  const showHotspotMapShell =
    viewMode === 'cuadricula' && (hasHotspots || metodoHotspot === 'area')
  const showAreaSelectionControl =
    viewMode === 'cuadricula' && metodoHotspot === 'area' && showHotspotMapShell
  const hasMapLayers =
    viewMode === 'cuadricula'
      ? showHotspotMapShell
      : hasChoropleth || (viewMode === 'detalle' && puntos.length > 0)
  const mapBusy = loadingBase || loadingOverlay || (isPage && pageBlocking)
  const interactionLocked = isPage && pageBlocking
  const currentViewHint = VIEW_MODES.find((m) => m.id === viewMode)?.hint ?? ''

  const territorioResumen = useMemo(
    () =>
      resolveTerritorioResumen({
        comunaId,
        barrioId,
        choroplethData: choroplethForResumen,
        lookupChoroplethData: territorioLookupChoropleth,
        desde,
        hasta,
        metrica: choroplethMetric,
      }),
    [
      comunaId,
      barrioId,
      choroplethForResumen,
      territorioLookupChoropleth,
      desde,
      hasta,
      choroplethMetric,
    ],
  )

  const territorioResumenLoading =
    Boolean(comunaId || barrioId) &&
    !territorioResumen &&
    (territorioLookupLoading || (mapBusy && viewMode !== 'cuadricula'))

  const legendScale = useMemo(() => {
    if (viewMode === 'cuadricula' && hotspotsData?.features?.length) {
      const densities = hotspotsData.features
        .map((f) => Number(f?.properties?.densidad_por_km2 || 0))
        .filter((d) => d > 0)
      return {
        kind: 'choropleth',
        title: `Densidad / km² (celda ${hotspotsData.meta?.tamano_celda_m ?? tamanoCeldaM} m)`,
        min: densities.length ? Math.min(...densities) : 0,
        max: Number(hotspotsData.meta?.densidad_max_km2 || 0),
        metrica: 'densidad',
        note: hotspotsData.meta?.malla_completa
          ? 'Gris = celda sin incidentes · color = densidad'
          : hotspotsData.meta?.celdas_recortadas
            ? 'Celdas recortadas al polígono · sin incidentes no se muestran'
            : 'Celdas sin incidentes no se muestran',
      }
    }
    if (viewMode === 'detalle' && showHeatLayer && puntos.length > 0) {
      return {
        kind: 'heat',
        title: 'Concentración',
        note: 'Zoom ≥14 → puntos',
      }
    }
    if (!choroplethMeta) return null
    return {
      kind: 'choropleth',
      title: choroplethMeta.metrica === 'conteo' ? 'Incidentes' : 'Densidad / km²',
      min: choroplethMeta.valor_min,
      max: choroplethMeta.valor_max,
      metrica: choroplethMeta.metrica,
      note: viewMode === 'detalle' ? 'Contorno territorial' : 'Gris = sin incidentes',
    }
  }, [viewMode, hotspotsData, choroplethMeta, tamanoCeldaM, showHeatLayer, puntos.length])

  const statusLine = useMemo(() => {
    const parts = [`${desde} → ${hasta}`]
    if (viewMode === 'cuadricula') {
      parts.push(
        metodoHotspot === 'area'
          ? 'Hotspots P14 · área dibujada'
          : `Hotspots P14 · celda ${tamanoCeldaM} m`,
      )
      if (hotspotsData?.meta) {
        const m = hotspotsData.meta
        if (m.malla_completa) {
          parts.push(
            `${m.celdas_con_incidentes ?? 0} con datos · ${m.celdas_devueltas ?? 0} en malla`,
          )
        } else {
          parts.push(`${m.celdas_devueltas ?? 0} celdas`)
        }
      }
      return parts.join(' · ')
    }
    if (!choroplethMeta) return parts.join(' · ')
    parts.push(choroplethMeta.nivel === 'barrio' ? 'Por barrios' : 'Por comunas')
    parts.push(choroplethMeta.metrica === 'conteo' ? 'Conteo' : 'Densidad / km²')
    if (viewMode === 'detalle' && pointsMeta) {
      parts.push(`${pointsMeta.puntos_devueltos?.toLocaleString('es-CO') ?? 0} puntos`)
    }
    return parts.join(' · ')
  }, [desde, hasta, choroplethMeta, viewMode, pointsMeta, hotspotsData, tamanoCeldaM, metodoHotspot])

  useEffect(() => {
    if (!onReportContextChange) return
    const comuna = (catalogos.comunas || []).find((c) => String(c.id) === String(comunaId))
    const barrio = (barrios || []).find((b) => String(b.id) === String(barrioId))
    const clase = (catalogos.clases_incidente || []).find((c) => String(c.id) === String(claseId))

    const filtros = {
      ...(desde ? { desde } : {}),
      ...(hasta ? { hasta } : {}),
      ...(comuna ? { comuna: comuna.nombre } : {}),
      ...(barrio ? { barrio: barrio.nombre } : {}),
      ...(clase ? { clase_incidente: clase.nombre } : {}),
      territorio: modoTerritorio === 'espacial' ? 'Polígono PostGIS' : 'Registro Mede',
      modo_vista:
        viewMode === 'territorio'
          ? 'Territorio'
          : viewMode === 'detalle'
            ? 'Detalle'
            : 'Hotspots',
    }
    const query = {
      ...(desde ? { desde } : {}),
      ...(hasta ? { hasta } : {}),
      ...(comunaId ? { comuna_id: comunaId } : {}),
      ...(barrioId ? { barrio_id: barrioId } : {}),
      ...(claseId ? { clase_incidente_id: claseId } : {}),
      ...(modoTerritorio === 'espacial' ? { territorio: 'espacial' } : {}),
      view_mode: viewMode,
      choropleth_metric: choroplethMetric,
      map_limite: mapLimite,
      tamano_celda_m: tamanoCeldaM,
      metodo_hotspot: metodoHotspot,
      ...(areaSelectionGeojson ? { geojson: areaSelectionGeojson } : {}),
    }
    onReportContextChange({ filtros, query, mapaLeyenda: legendScale })
  }, [
    onReportContextChange,
    desde,
    hasta,
    comunaId,
    barrioId,
    claseId,
    modoTerritorio,
    viewMode,
    choroplethMetric,
    mapLimite,
    tamanoCeldaM,
    metodoHotspot,
    areaSelectionGeojson,
    catalogos,
    barrios,
    legendScale,
  ])

  const hotspotsCoincidenConFiltro = hotspotsMatchTerritoryFilter(hotspotsData, comunaId, barrioId)
  const areaHotspotsListos =
    metodoHotspot === 'area' &&
    Boolean(areaSelectionGeojson) &&
    hasHotspots &&
    !areaEditorBlocksMap &&
    hotspotsMatchAreaSelection(hotspotsData, areaSelectionGeojson)
  const showHotspotRankLabels =
    forceShowHotspotCellIds ||
    areaHotspotsListos ||
    ((Boolean(comunaId) || Boolean(barrioId)) && hotspotsCoincidenConFiltro)

  if (!initOk && !isPage) {
    return (
      <div className="landing-map-shell landing-map-loading muted" role="status">
        Preparando mapa…
      </div>
    )
  }

  return (
    <>
      {isPage && pageBlocking && (
        <div
          className="map-page-blocking-overlay"
          role="alertdialog"
          aria-modal="true"
          aria-labelledby="map-page-blocking-title"
          aria-describedby="map-page-blocking-desc"
        >
          <div className="map-page-blocking-card">
            <h2 id="map-page-blocking-title">Cargando sección mapa</h2>
            <p id="map-page-blocking-desc" className="muted small">
              {pageBlockingMsg}
            </p>
            <div className="map-page-progress" role="progressbar" aria-valuenow={loadProgress} aria-valuemin={0} aria-valuemax={100}>
              <div className="map-page-progress-track">
                <div className="map-page-progress-fill" style={{ width: `${loadProgress}%` }} />
              </div>
              <span className="map-page-progress-pct">{loadProgress}%</span>
            </div>
            <p className="muted small">
              Precarga de capas e indicadores en caché. Los cambios de vista y métrica posteriores serán
              instantáneos si ya están guardados ({listCachedFilterKeys().length} combinación
              {listCachedFilterKeys().length === 1 ? '' : 'es'} de filtros en memoria).
            </p>
          </div>
        </div>
      )}

      <div
        className={`landing-map-page-root${isPage ? ' is-page-variant' : ''}${interactionLocked ? ' is-interaction-locked' : ''}`}
        inert={interactionLocked ? true : undefined}
      >
      <div className="landing-map-workspace">
        <aside className="landing-map-sidebar panel">
          <h3 className="landing-map-sidebar-title">Explorar mapa</h3>

          <div className="landing-map-section">
            <span className="landing-map-section-label">Periodo</span>
            <div className="landing-map-row-2">
              <label className="filter-field">
                Desde
                <input type="date" value={desde} onChange={(e) => setDesde(e.target.value)} min={selMin} max={hasta} />
              </label>
              <label className="filter-field">
                Hasta
                <input type="date" value={hasta} onChange={(e) => setHasta(e.target.value)} min={desde} max={selMax} />
              </label>
            </div>
          </div>

          <div className="landing-map-section">
            <span className="landing-map-section-label">Territorio</span>
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
              <select value={barrioId} onChange={(e) => setBarrioId(e.target.value)} disabled={!comunaId}>
                <option value="">Todos</option>
                {barrios.map((b) => (
                  <option key={b.id} value={String(b.id)}>
                    {b.nombre}
                  </option>
                ))}
              </select>
            </label>
            <label className="filter-field">
              Clase
              <select value={claseId} onChange={(e) => setClaseId(e.target.value)}>
                <option value="">Todas</option>
                {(catalogos.clases_incidente || []).map((c) => (
                  <option key={c.id} value={String(c.id)}>
                    {c.nombre}
                  </option>
                ))}
              </select>
            </label>
            {(comunaId || barrioId) && (
              <MapTerritorioResumenPanel
                resumen={territorioResumen}
                loading={territorioResumenLoading}
                compact
              />
            )}
          </div>

          <div className="landing-map-section">
            <span className="landing-map-section-label">Visualización</span>
            <div className="landing-map-segments" role="group" aria-label="Modo de visualización">
              {VIEW_MODES.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  className={`landing-map-segment${viewMode === m.id ? ' is-active' : ''}`}
                  onClick={() => setViewMode(m.id)}
                  title={m.hint}
                >
                  {m.label}
                </button>
              ))}
            </div>
            <p className="muted small landing-map-mode-hint">{currentViewHint}</p>
            {viewMode === 'cuadricula' && (
              <p className="muted small landing-map-mode-detail">
                Celdas de 300–500 m coloreadas por densidad. En «Área en mapa», use el control del mapa para dibujar un
                polígono y acotar el análisis. Compare con Territorio y haga clic en una celda del ranking.
              </p>
            )}
            {viewMode !== 'cuadricula' && (
              <>
                <label className="filter-field">
                  Intensidad
                  <select value={choroplethMetric} onChange={(e) => setChoroplethMetric(e.target.value)}>
                    <option value="densidad">Densidad (incidentes / km²)</option>
                    <option value="conteo">Número de incidentes</option>
                  </select>
                </label>
                <p className="muted small landing-map-filter-help">
                  {INTENSIDAD_HELP[choroplethMetric] ?? INTENSIDAD_HELP.densidad}
                </p>
              </>
            )}
            {viewMode === 'territorio' && choroplethMetric === 'densidad' && (
              <p className="muted small landing-map-filter-help">{RATIO_VS_CIUDAD_HELP}</p>
            )}
          </div>

          <details
            className="landing-map-advanced"
            open={showAdvanced}
            onToggle={(e) => setShowAdvanced(e.target.open)}
          >
            <summary>Opciones avanzadas</summary>
            <label className="filter-field">
              Territorio en filtros
              <select value={modoTerritorio} onChange={(e) => setModoTerritorio(e.target.value)}>
                <option value="registro">Registro Mede</option>
                <option value="espacial">Polígono PostGIS</option>
              </select>
            </label>
            <p className="muted small landing-map-filter-help">
              {TERRITORIO_FILTRO_HELP[modoTerritorio] ?? TERRITORIO_FILTRO_HELP.registro}
            </p>
            {viewMode === 'detalle' && (
              <label className="filter-field">
                Tope de puntos
                <select value={mapLimite} onChange={(e) => setMapLimite(normalizeMapLimite(e.target.value))}>
                  {MAP_LIMITE_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {viewMode === 'cuadricula' && (
              <>
                {metodoHotspot === 'cuadricula' ? (
                  <label className="filter-field">
                    Tamaño celda (m)
                    <select value={tamanoCeldaM} onChange={(e) => setTamanoCeldaM(e.target.value)}>
                      {HOTSPOT_CELDA_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </label>
                ) : null}
                <label className="filter-field">
                  Método
                  <select
                    value={metodoHotspot}
                    onChange={(e) => {
                      const v = e.target.value
                      setMetodoHotspot(v)
                      if (v === 'area') {
                        setTamanoCeldaM(HOTSPOT_CELDA_AREA_M)
                      } else {
                        setAreaSelectionGeojson(null)
                        setAreaEditorPhase('inactive')
                        areaDismissedForGeojsonRef.current = null
                        if (tamanoCeldaM === HOTSPOT_CELDA_AREA_M) setTamanoCeldaM('300')
                      }
                    }}
                  >
                    <option value="cuadricula">Cuadrícula (filtros)</option>
                    <option value="area">Área en mapa</option>
                  </select>
                </label>
                {metodoHotspot === 'area' && (
                  <>
                    <p className="muted small landing-map-area-hint">
                      <strong>Dibujar:</strong> botón del mapa → vértices → cierre en el punto verde → «Cargar /
                      actualizar filtros».
                      <br />
                      <strong>Celdas:</strong> pase el cursor para ver incidentes y % del área; clic para detalle.
                      <br />
                      <strong>Redibujar / Borrar:</strong> botones abajo cuando ya hay un área definida.
                    </p>
                    {areaSelectionGeojson && (
                      <div className="landing-map-area-actions">
                        {hasHotspots && !areaEditorBlocksMap && (
                          <button
                            type="button"
                            className="btn btn-secondary landing-map-area-redraw"
                            onClick={handleRedrawArea}
                            disabled={mapBusy}
                          >
                            Redibujar área
                          </button>
                        )}
                        <button
                          type="button"
                          className="btn btn-secondary landing-map-area-clear"
                          onClick={handleClearAreaSelection}
                          disabled={mapBusy}
                        >
                          Borrar área
                        </button>
                      </div>
                    )}
                  </>
                )}
              </>
            )}
          </details>

          <button
            type="button"
            className="btn btn-primary landing-map-apply"
            onClick={() => {
              if (isPage) void ensureFilterBundleData({ forceRefresh: false, showBlocking: true })
              else void loadMap()
            }}
            disabled={mapBusy || !desde || !hasta}
          >
            {mapBusy
              ? 'Actualizando…'
              : isPage && filtersCached
                ? 'Aplicar filtros (caché)'
                : 'Cargar / actualizar filtros'}
          </button>
        </aside>

        <div className="landing-map-main">
          {err && <p className="form-error landing-map-form-error">{err}</p>}

          {statusLine && (
            <div className="landing-map-statusbar">
              <span>{statusLine}</span>
              {mapBusy && <span className="landing-map-statusbar-loading">Cargando…</span>}
            </div>
          )}

          {viewMode === 'cuadricula' && metodoHotspot === 'area' && (
            <p className="landing-map-area-size-tip landing-map-area-size-tip-main" role="note">
              {HOTSPOT_AREA_POLYGON_TIP}
            </p>
          )}

          {viewMode === 'cuadricula' && metodoHotspot === 'area' && areaSelectionGeojson && (
            <MapAreaAnalisisPanel
              resumen={hotspotsData?.meta?.area_resumen}
              loading={mapBusy && !hotspotsData?.meta?.area_resumen}
            />
          )}

          {viewMode !== 'cuadricula' && (comunaId || barrioId) && (
            <MapTerritorioResumenPanel
              resumen={territorioResumen}
              loading={territorioResumenLoading}
            />
          )}

          {barrioSinPoligono && (
            <p className="landing-map-barrio-sin-poligono muted small" role="status">
              El barrio seleccionado no tiene polígono cartográfico cargado en el sistema (límite
              oficial en PostGIS). Se muestra el contorno de la comuna; los incidentes del barrio
              siguen aplicándose en los filtros.
            </p>
          )}

          <div className="landing-map-view-wrap">
            {!hasMapLayers && !mapBusy ? (
              <div className="landing-map-shell landing-map-empty muted" role="status">
                {hotspotsData?.meta?.malla_area_excedida
                  ? hotspotsData.meta.descripcion
                  : viewMode === 'cuadricula' && metodoHotspot === 'area'
                    ? 'Dibuje un área en el mapa (control de selección) y aplique los filtros.'
                    : barrioId
                      ? 'El barrio seleccionado no tiene geometría en el mapa y no hay contorno comunal disponible para estos filtros.'
                      : 'Sin datos para estos filtros. Amplíe el periodo o quite filtros.'}
              </div>
            ) : (
              <div
                className="landing-map-shell"
                id={isPage ? 'map-page-shell' : 'landing-map-shell'}
                aria-label="Mapa de concentración de incidentes"
              >
                {legendScale && (
                  <div
                    className={`landing-map-legend-card${legendScale.kind === 'heat' ? ' is-compact' : ''}`}
                  >
                    <span className="landing-map-legend-title">{legendScale.title}</span>
                    {legendScale.kind === 'heat' ? (
                      <div className="landing-map-heat-legend" aria-hidden="true">
                        <span className="landing-map-heat-legend-label">Baja</span>
                        <span className="landing-map-heat-legend-bar" />
                        <span className="landing-map-heat-legend-label">Alta</span>
                      </div>
                    ) : (
                      <div className="landing-map-choropleth-legend" aria-hidden="true">
                        <span className="landing-map-choropleth-legend-label">
                          {fmtChoroplethVal(legendScale.max, legendScale.metrica)}
                        </span>
                        <span className="landing-map-choropleth-legend-bar" />
                        <span className="landing-map-choropleth-legend-label">
                          {fmtChoroplethVal(legendScale.min, legendScale.metrica)}
                        </span>
                      </div>
                    )}
                    {legendScale.note && (
                      <span className="landing-map-legend-note muted small">{legendScale.note}</span>
                    )}
                  </div>
                )}

                {mapBusy && (
                  <div className="landing-map-refresh-overlay muted small" role="status">
                    {viewMode === 'detalle' && loadingOverlay && !loadingBase
                      ? 'Cargando incidentes…'
                      : viewMode === 'cuadricula'
                        ? 'Cargando cuadrícula P14…'
                        : loadingBase
                          ? 'Cargando territorios…'
                          : 'Cargando capa adicional…'}
                  </div>
                )}

                <MapContainer
                  center={DEFAULT_CENTER}
                  zoom={DEFAULT_ZOOM}
                  className="landing-map-leaflet"
                  style={{ height: '100%', width: '100%' }}
                  scrollWheelZoom
                  preferCanvas
                >
                  <MapResizeEffects compact={compact} />
                  <MapZoomTracker onZoom={handleMapZoom} />
                  <MapFlyTo focus={mapFocus} />
                  <TileLayer
                    attribution='&copy; OpenStreetMap'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  {hasChoropleth && viewMode !== 'cuadricula' && (
                    <>
                      <ChoroplethLayer
                        geojson={mapChoroplethData}
                        comunaId={comunaId}
                        barrioId={barrioSinPoligono ? '' : barrioId}
                        subdued={viewMode === 'detalle'}
                      />
                      <MapFitBoundsOnce geojson={mapChoroplethData} enabled={!mapFocus} />
                    </>
                  )}
                  {viewMode === 'cuadricula' && hasHotspots && (
                    <>
                      <HotspotGridLayer
                        geojson={hotspotsData}
                        editorBlocksMap={metodoHotspot === 'area' && areaEditorBlocksMap}
                        areaSelectionActive={
                          metodoHotspot === 'area' && Boolean(areaSelectionGeojson)
                        }
                        showCellIds={showHotspotRankLabels}
                        cellIdMaxRank={
                          forceShowHotspotCellIds
                            ? HOTSPOT_CAPTURE_LABEL_MAX_RANK
                            : showHotspotRankLabels
                              ? HOTSPOT_MAP_LABEL_MAX_RANK
                              : null
                        }
                        cellIdLabelMode="rank"
                      />
                      {metodoHotspot === 'area' && areaSelectionGeojson && (
                        <MapAreaOutline geometryJson={areaSelectionGeojson} />
                      )}
                      <MapFitBoundsOnce geojson={hotspotsData} enabled={!mapFocus} />
                    </>
                  )}
                  {viewMode === 'cuadricula' && metodoHotspot === 'area' && areaSelectionGeojson && !hasHotspots && (
                    <MapAreaOutline geometryJson={areaSelectionGeojson} />
                  )}
                  {viewMode === 'detalle' && puntos.length > 0 && (
                    <DetailPointsLayer
                      puntos={puntos}
                      showHeat={showHeatLayer}
                      showMarkers={showPointMarkers}
                      mapZoom={mapZoom}
                    />
                  )}
                  {showAreaSelectionControl && (
                    <MapAreaSelection
                      ref={areaSelectionRef}
                      enabled
                      onAreaChange={handleAreaSelectionChange}
                      onPhaseChange={handleAreaEditorPhaseChange}
                    />
                  )}
                </MapContainer>
              </div>
            )}
          </div>
        </div>
      </div>

      <LandingCalidadTerritorio
        desde={desde}
        hasta={hasta}
        comunaId={comunaId}
        barrioId={barrioId}
        claseId={claseId}
        modoTerritorio={modoTerritorio}
        enabled={initOk && !interactionLocked}
        controlled={isPage}
        externalData={isPage ? calidadData : null}
        externalLoading={isPage ? indicatorsLoading || pageBlocking : false}
        externalErr={isPage ? indicatorsErr : null}
      />

      <LandingGeoIndicators
        desde={desde}
        hasta={hasta}
        comunaId={comunaId}
        barrioId={barrioId}
        claseId={claseId}
        modoTerritorio={modoTerritorio}
        tamanoCeldaM={tamanoCeldaM}
        enabled={initOk && !interactionLocked}
        onFocusCell={focusCellOnMap}
        controlled={isPage}
        externalDensidad={isPage ? densidadData : null}
        externalRanking={isPage ? rankingData : null}
        externalLoading={isPage ? indicatorsLoading || pageBlocking : false}
        externalErr={isPage ? indicatorsErr : null}
        nivelDensidad={isPage ? nivelDensidad : undefined}
        onNivelDensidadChange={isPage ? handleNivelDensidadChange : undefined}
      />
      </div>
    </>
  )
}
