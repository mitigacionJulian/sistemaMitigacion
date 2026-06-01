import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'
import { MapContainer, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import { L } from '../map/leafletPlugins.js'
import {
  fetchDashboardBarrios,
  fetchDashboardCatalogos,
  fetchDashboardChoroplethTerritorial,
  fetchDashboardHotspotsCuadricula,
  fetchDashboardMapaDetalle,
  fetchDashboardRangoFechas,
} from '../api/client.js'
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

const HOTSPOT_CELDA_OPTIONS = [
  { value: '300', label: '300 m — más detalle' },
  { value: '500', label: '500 m — más suave' },
]

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

function resolveChoroplethNivel(comunaId, barrioId) {
  if (barrioId || comunaId) return 'barrio'
  return 'comuna'
}

function fmtChoroplethVal(v, metrica) {
  if (v == null || Number.isNaN(Number(v))) return '—'
  if (metrica === 'conteo') return Number(v).toLocaleString('es-CO')
  return Number(v).toLocaleString('es-CO', { maximumFractionDigits: 2 })
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
        leafletLayer.bindPopup(
          `<div class="landing-map-popup"><strong>${escapeHtml(titulo)}</strong><br/>` +
            `Incidentes: <strong>${escapeHtml(p.incidentes)}</strong><br/>` +
            `Densidad: <strong>${fmtChoroplethVal(p.densidad_km2, 'densidad')}</strong> / km²</div>`,
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

function HotspotGridLayer({ geojson }) {
  const map = useMap()
  useEffect(() => {
    if (!geojson?.features?.length) return undefined
    const maxD = Number(geojson.meta?.densidad_max_km2 || 0)
    const densities = geojson.features
      .map((f) => Number(f?.properties?.densidad_por_km2 || 0))
      .filter((d) => d > 0)
    const minD = densities.length ? Math.min(...densities) : 0

    const layer = L.geoJSON(geojson, {
      style: (feature) => {
        const d = Number(feature?.properties?.densidad_por_km2 || 0)
        return choroplethStyle(d, minD, maxD, d <= 0, false, 0.82)
      },
      onEachFeature: (feature, leafletLayer) => {
        const p = feature?.properties || {}
        leafletLayer.bindPopup(
          `<div class="landing-map-popup"><strong>Celda P14</strong><br/>` +
            `Incidentes: <strong>${escapeHtml(p.conteo)}</strong><br/>` +
            `Densidad: <strong>${fmtChoroplethVal(p.densidad_por_km2, 'densidad')}</strong> / km²<br/>` +
            `Área celda: <strong>${fmtChoroplethVal(p.area_km2, 'densidad')}</strong> km²</div>`,
        )
      },
    })
    layer.addTo(map)
    return () => map.removeLayer(layer)
  }, [map, geojson])
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

export function LandingIncidentMap() {
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
  const [showAdvanced, setShowAdvanced] = useState(false)

  const [choroplethData, setChoroplethData] = useState(null)
  const [pointsData, setPointsData] = useState(null)
  const [hotspotsData, setHotspotsData] = useState(null)
  const [err, setErr] = useState(null)
  const [initOk, setInitOk] = useState(false)
  const [loadingBase, setLoadingBase] = useState(false)
  const [loadingOverlay, setLoadingOverlay] = useState(false)
  const [mapZoom, setMapZoom] = useState(DEFAULT_ZOOM)
  const [mapFocus, setMapFocus] = useState(null)

  const loadGenRef = useRef(0)
  const handleMapZoom = useCallback((z) => setMapZoom(z), [])
  const focusCellOnMap = useCallback((lat, lon) => {
    if (lat == null || lon == null) return
    setViewMode('cuadricula')
    setMapFocus({ lat: Number(lat), lon: Number(lon), zoom: 15, ts: Date.now() })
    document.getElementById('landing-map-shell')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [])

  useEffect(() => {
    setMapFocus(null)
  }, [desde, hasta, comunaId, barrioId, claseId, modoTerritorio, tamanoCeldaM, metodoHotspot])

  const showPointMarkers = mapZoom >= DETAIL_POINTS_MIN_ZOOM
  const showHeatLayer = mapZoom < DETAIL_POINTS_MIN_ZOOM

  const selMin = rangoMeta?.selector_fecha_min ?? FECHAS_REF_MEDE.selector_fecha_min
  const selMax = rangoMeta?.selector_fecha_max ?? FECHAS_REF_MEDE.selector_fecha_max

  const buildBaseParams = useCallback(() => {
    const comunaQ = queryId(comunaId)
    const barrioQ = queryId(barrioId)
    const claseQ = queryId(claseId)
    return {
      desde,
      hasta,
      ...(comunaQ !== undefined ? { comuna_id: comunaQ } : {}),
      ...(barrioQ !== undefined ? { barrio_id: barrioQ } : {}),
      ...(claseQ !== undefined ? { clase_incidente_id: claseQ } : {}),
      ...(modoTerritorio === 'espacial' ? { territorio: 'espacial' } : {}),
    }
  }, [desde, hasta, comunaId, barrioId, claseId, modoTerritorio])

  const loadMap = useCallback(async () => {
    if (!desde || !hasta) return
    const gen = loadGenRef.current + 1
    loadGenRef.current = gen
    setErr(null)
    setLoadingBase(true)
    setLoadingOverlay(viewMode !== 'territorio')

    const baseParams = buildBaseParams()
    const nivel = resolveChoroplethNivel(comunaId, barrioId)
    const choroplethParams = { ...baseParams, nivel, metrica: choroplethMetric }

    try {
      if (viewMode === 'cuadricula') {
        const hotspots = await fetchDashboardHotspotsCuadricula({
          ...baseParams,
          metodo: metodoHotspot,
          tamano_celda_m: Number(tamanoCeldaM) || 300,
        })
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
    viewMode,
    mapLimite,
    choroplethMetric,
    tamanoCeldaM,
    metodoHotspot,
  ])

  useEffect(() => {
    if (!mapFocus || viewMode !== 'cuadricula' || !desde || !hasta) return
    void loadMap()
  }, [mapFocus?.ts, viewMode, desde, hasta, loadMap])

  useEffect(() => {
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

  const puntos = useMemo(() => pointsData?.puntos ?? [], [pointsData])
  const choroplethMeta = choroplethData?.meta
  const pointsMeta = pointsData?.meta
  const hasChoropleth = (choroplethData?.features?.length ?? 0) > 0
  const hasHotspots = (hotspotsData?.features?.length ?? 0) > 0
  const hasMapLayers =
    viewMode === 'cuadricula' ? hasHotspots : hasChoropleth || (viewMode === 'detalle' && puntos.length > 0)
  const mapBusy = loadingBase || loadingOverlay
  const currentViewHint = VIEW_MODES.find((m) => m.id === viewMode)?.hint ?? ''

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
        note: 'Celdas sin incidentes no se muestran',
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
      parts.push(`Hotspots P14 · celda ${tamanoCeldaM} m`)
      if (hotspotsData?.meta) {
        parts.push(`${hotspotsData.meta.celdas_devueltas ?? 0} celdas`)
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
  }, [desde, hasta, choroplethMeta, viewMode, pointsMeta, hotspotsData, tamanoCeldaM])

  if (!initOk) {
    return (
      <div className="landing-map-shell landing-map-loading muted" role="status">
        Preparando mapa…
      </div>
    )
  }

  return (
    <>
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
                Celdas de 300–500 m coloreadas por densidad. Localiza tramos concretos que en Territorio se diluyen al
                promediar toda la comuna. Filtre por comuna, compare ambos modos y haga clic en una celda.
              </p>
            )}
            {viewMode !== 'cuadricula' && (
              <label className="filter-field">
                Intensidad
                <select value={choroplethMetric} onChange={(e) => setChoroplethMetric(e.target.value)}>
                  <option value="densidad">Densidad (incidentes / km²)</option>
                  <option value="conteo">Número de incidentes</option>
                </select>
              </label>
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
                <label className="filter-field">
                  Método
                  <select value={metodoHotspot} onChange={(e) => setMetodoHotspot(e.target.value)}>
                    <option value="cuadricula">Cuadrícula</option>
                    <option value="dbscan">DBSCAN</option>
                  </select>
                </label>
              </>
            )}
          </details>

          <button
            type="button"
            className="btn btn-primary landing-map-apply"
            onClick={() => void loadMap()}
            disabled={mapBusy || !desde || !hasta}
          >
            {mapBusy ? 'Actualizando…' : 'Actualizar mapa'}
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

          <div className="landing-map-view-wrap">
            {!hasMapLayers && !mapBusy ? (
              <div className="landing-map-shell landing-map-empty muted" role="status">
                Sin datos para estos filtros. Amplíe el periodo o quite filtros.
              </div>
            ) : (
              <div className="landing-map-shell" id="landing-map-shell" aria-label="Mapa de concentración de incidentes">
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
                        geojson={choroplethData}
                        comunaId={comunaId}
                        barrioId={barrioId}
                        subdued={viewMode === 'detalle'}
                      />
                      <MapFitBoundsOnce geojson={choroplethData} enabled={!mapFocus} />
                    </>
                  )}
                  {viewMode === 'cuadricula' && hasHotspots && (
                    <>
                      <HotspotGridLayer geojson={hotspotsData} />
                      <MapFitBoundsOnce geojson={hotspotsData} enabled={!mapFocus} />
                    </>
                  )}
                  {viewMode === 'detalle' && puntos.length > 0 && (
                    <DetailPointsLayer
                      puntos={puntos}
                      showHeat={showHeatLayer}
                      showMarkers={showPointMarkers}
                      mapZoom={mapZoom}
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
        enabled={initOk}
      />

      <LandingGeoIndicators
        desde={desde}
        hasta={hasta}
        comunaId={comunaId}
        barrioId={barrioId}
        claseId={claseId}
        modoTerritorio={modoTerritorio}
        tamanoCeldaM={tamanoCeldaM}
        enabled={initOk}
        onFocusCell={focusCellOnMap}
      />
    </>
  )
}
