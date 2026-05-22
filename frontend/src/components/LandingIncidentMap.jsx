import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import { L } from '../map/leafletPlugins.js'
import {
  fetchDashboardBarrios,
  fetchDashboardCatalogos,
  fetchDashboardIncidentesMapa,
  fetchDashboardRangoFechas,
} from '../api/client.js'

/** Centro por defecto (área metropolitana de Medellín) si aún no hay puntos para calcular extensión. */
const DEFAULT_CENTER = [6.2476, -75.5659]

const FECHAS_REF_MEDE = {
  default_desde: '2021-01-01',
  default_hasta: '2021-09-30',
  selector_fecha_min: '2014-01-01',
  selector_fecha_max: '2021-09-30',
}

/** Opciones de tope de puntos (alineadas con el backend, máx. 100.000 filas). */
const MAP_LIMITE_OPTIONS = [
  { value: '5000', label: '5.000 — ligero, rápido' },
  { value: '10000', label: '10.000 — equilibrado (recomendado por año)' },
  { value: '20000', label: '20.000' },
  { value: '40000', label: '40.000' },
  { value: '70000', label: '70.000' },
  { value: '100000', label: '100.000 — máximo del servidor (histórico largo)' },
]

const MAP_LIMITE_ALLOWED = new Set(MAP_LIMITE_OPTIONS.map((o) => o.value))

/** Valor inicial del selector de tope de puntos (debe coincidir con el bootstrap). */
const DEFAULT_MAP_LIMITE = '10000'
/** Mismo tope que `MAPA_CAP_SIN_LIMITE` en el backend (solo texto de ayuda). */
const MAPA_CAP_SIN_LIMITE_UI = 100_000

function normalizeMapLimite(raw) {
  return MAP_LIMITE_ALLOWED.has(String(raw)) ? String(raw) : DEFAULT_MAP_LIMITE
}

/** Texto de ayuda sobre coste de cargar muchos puntos (mapa calor + clusters). */
function mapLimiteHelpText(mapLimite) {
  const n = Number(mapLimite)
  const cap = MAPA_CAP_SIN_LIMITE_UI.toLocaleString('es-CO')
  const base =
    'Cada punto implica más trabajo en PostgreSQL, más datos por red y más carga en el navegador (capa de calor y agrupación de marcadores).'
  if (n <= 10_000) {
    return `${base} Hasta 10.000 suele ir bien para consultas por año o periodos cortos.`
  }
  if (n <= 40_000) {
    return `${base} Entre 20.000 y 40.000 puede notarse lentitud al cambiar filtros o al mover el mapa.`
  }
  if (n < 100_000) {
    return `${base} 70.000 puntos ya es pesado para equipos modestos: espere varios segundos y posible uso alto de memoria.`
  }
  return `${base} 100.000 es el máximo que devuelve el servidor: sirve para ver mucho histórico de una vez, pero la página puede tardar y volverse lenta. Si en el periodo hay más de ${cap} incidentes con coordenadas, solo se muestran los más recientes dentro de ese tope.`
}

const VIEWPORT_COMPACT_PX = 640

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

function escapeHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/** Convierte id de select (string) a número para querystring; vacío → undefined. */
function queryId(v) {
  if (v === '' || v === undefined || v === null) return undefined
  const n = Number(v)
  return Number.isFinite(n) ? n : undefined
}

function mapFilterSig(desde, hasta, comunaId, barrioId, claseId, mapLimite) {
  return `${desde}|${hasta}|${comunaId}|${barrioId}|${claseId}|${mapLimite}`
}

function MapBoundsEffect({ puntos }) {
  const map = useMap()
  useEffect(() => {
    if (!puntos?.length) return
    if (puntos.length === 1) {
      map.setView([puntos[0].latitud, puntos[0].longitud], 14)
      return
    }
    const bounds = L.latLngBounds(puntos.map((p) => [p.latitud, p.longitud]))
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [28, 28], maxZoom: 14 })
    }
  }, [map, puntos])
  return null
}

/** Recalcula tamaño del mapa al cambiar viewport o ventana (layout responsivo). */
function MapResizeEffects({ compact }) {
  const map = useMap()
  useEffect(() => {
    const id = requestAnimationFrame(() => map.invalidateSize())
    return () => cancelAnimationFrame(id)
  }, [map, compact])

  useEffect(() => {
    const onResize = () => map.invalidateSize()
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [map])

  return null
}

/**
 * Capa de calor (densidad aparente) + agrupación al acercar zoom.
 * Los filtros solo cambian `puntos`; este efecto limpia y vuelve a crear capas.
 */
function ClusterHeatLayers({ puntos, compact }) {
  const map = useMap()

  useEffect(() => {
    if (!puntos?.length) return

    const heatLatLngs = puntos.map((p) => [p.latitud, p.longitud, 0.4])
    const heatRadius = compact ? 16 : 24
    const heatBlur = compact ? 12 : 18
    const gradient = {
      0.0: 'rgba(248,250,252,0)',
      0.35: 'rgba(20,184,166,0.35)',
      0.65: 'rgba(15,118,110,0.55)',
      1.0: 'rgba(13,148,136,0.78)',
    }

    const heat = L.heatLayer(heatLatLngs, {
      radius: heatRadius,
      blur: heatBlur,
      maxZoom: 17,
      max: 1.15,
      minOpacity: 0.1,
      gradient,
    })
    map.addLayer(heat)

    const dotIcon = L.divIcon({
      className: 'landing-map-cluster-dot',
      html: '',
      iconSize: [10, 10],
      iconAnchor: [5, 5],
    })

    const mcg = L.markerClusterGroup({
      chunkedLoading: true,
      chunkInterval: 200,
      showCoverageOnHover: false,
      maxClusterRadius: compact ? 48 : 68,
      disableClusteringAtZoom: 16,
      spiderfyOnMaxZoom: true,
      zoomToBoundsOnClick: true,
    })

    for (let i = 0; i < puntos.length; i++) {
      const p = puntos[i]
      const m = L.marker([p.latitud, p.longitud], { icon: dotIcon })
      const cls = escapeHtml(p.clase_incidente || '—')
      const rad = escapeHtml(p.radicado ?? '')
      const fec = escapeHtml(p.fecha_incidente ?? '')
      m.bindPopup(
        `<div class="landing-map-popup"><strong>${rad}</strong><br/>${fec}<br/>${cls}</div>`,
      )
      mcg.addLayer(m)
    }
    map.addLayer(mcg)

    return () => {
      map.removeLayer(heat)
      map.removeLayer(mcg)
    }
  }, [map, puntos, compact])

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
  const [mapLimite, setMapLimite] = useState(DEFAULT_MAP_LIMITE)

  const [data, setData] = useState(null)
  const [err, setErr] = useState(null)
  const [initOk, setInitOk] = useState(false)
  const [mapLoading, setMapLoading] = useState(false)
  /** Incrementa en cada respuesta OK para forzar remount del mapa (capas Leaflet). */
  const [mapDataStamp, setMapDataStamp] = useState(0)
  /** Firma de la última respuesta OK; evita refetch duplicado y doble efecto en Strict Mode. */
  const lastFetchedSigRef = useRef('')

  const selMin = rangoMeta?.selector_fecha_min ?? FECHAS_REF_MEDE.selector_fecha_min
  const selMax = rangoMeta?.selector_fecha_max ?? FECHAS_REF_MEDE.selector_fecha_max

  const loadMap = useCallback(async () => {
    if (!desde || !hasta) return
    setMapLoading(true)
    setErr(null)
    try {
      const comunaQ = queryId(comunaId)
      const barrioQ = queryId(barrioId)
      const claseQ = queryId(claseId)
      const limiteApi = Number(mapLimite)
      const params = {
        desde,
        hasta,
        limite: Number.isFinite(limiteApi) ? limiteApi : Number(DEFAULT_MAP_LIMITE),
        ...(comunaQ !== undefined ? { comuna_id: comunaQ } : {}),
        ...(barrioQ !== undefined ? { barrio_id: barrioQ } : {}),
        ...(claseQ !== undefined ? { clase_incidente_id: claseQ } : {}),
      }
      const payload = await fetchDashboardIncidentesMapa(params)
      setData(payload)
      lastFetchedSigRef.current = mapFilterSig(desde, hasta, comunaId, barrioId, claseId, mapLimite)
      setMapDataStamp((n) => n + 1)
    } catch (e) {
      setErr(e instanceof Error ? e.message : 'No se pudo cargar el mapa')
      setData(null)
    } finally {
      setMapLoading(false)
    }
  }, [desde, hasta, comunaId, barrioId, claseId, mapLimite])

  useEffect(() => {
    if (!initOk || !desde || !hasta) return
    const sig = mapFilterSig(desde, hasta, comunaId, barrioId, claseId, mapLimite)
    if (sig === lastFetchedSigRef.current) return
    const t = window.setTimeout(() => {
      void loadMap()
    }, 450)
    return () => window.clearTimeout(t)
  }, [desde, hasta, comunaId, barrioId, claseId, mapLimite, initOk, loadMap])

  useEffect(() => {
    let alive = true
    ;(async () => {
      try {
        const [rango, cats] = await Promise.all([
          fetchDashboardRangoFechas().catch(() => ({
            ...FECHAS_REF_MEDE,
            hay_datos: false,
            referencia_fuente:
              'No se pudo leer el rango desde el servidor; usando fechas de referencia del archivo Mede depurado.',
          })),
          fetchDashboardCatalogos().catch(() => ({ comunas: [], clases_incidente: [] })),
        ])
        if (!alive) return
        setRangoMeta(rango)
        setCatalogos(cats)
        const d = rango.default_desde
        const h = rango.default_hasta
        setDesde(d)
        setHasta(h)

        setMapLoading(true)
        const payload = await fetchDashboardIncidentesMapa({
          desde: d,
          hasta: h,
          limite: Number(DEFAULT_MAP_LIMITE),
        })
        if (!alive) return
        setData(payload)
        lastFetchedSigRef.current = mapFilterSig(d, h, '', '', '', DEFAULT_MAP_LIMITE)
        setMapDataStamp((n) => n + 1)
        setErr(null)
      } catch (e) {
        if (!alive) return
        setErr(e instanceof Error ? e.message : 'No se pudo cargar el mapa')
        setData(null)
      } finally {
        if (alive) {
          setMapLoading(false)
          setInitOk(true)
        }
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

  const puntos = useMemo(() => data?.puntos ?? [], [data])
  const meta = data?.meta

  const mapInstanceKey = useMemo(
    () => `${desde}|${hasta}|${comunaId}|${barrioId}|${claseId}|${mapLimite}|${mapDataStamp}`,
    [desde, hasta, comunaId, barrioId, claseId, mapLimite, mapDataStamp],
  )

  if (!initOk) {
    return (
      <div className="landing-map-shell landing-map-loading muted" role="status">
        Cargando rango de fechas, catálogos y primer mapa…
      </div>
    )
  }

  return (
    <>
      <div className="landing-map-filters panel">
        <h3 className="landing-map-filters-title">Filtros (mismos endpoints que el tablero)</h3>
        <p className="muted small filter-help">
          Usa <code>rango-fechas</code> para límites del selector, <code>catalogos</code> / <code>barrios</code> para
          listas y <code>incidentes-mapa</code> con <code>desde</code>, <code>hasta</code>,{' '}
          <code>comuna_id</code>, <code>barrio_id</code>, <code>clase_incidente_id</code> y <code>limite</code> (100 a
          100.000 filas, o <code>0</code> para el modo automático hasta el tope del servidor). Al cambiar fechas, listas
          o el tope se vuelve a consultar el mapa en unos instantes; use <strong>Aplicar al mapa</strong> para forzar de
          inmediato.
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
            <select value={claseId} onChange={(e) => setClaseId(e.target.value)}>
              <option value="">Todas</option>
              {(catalogos.clases_incidente || []).map((c) => (
                <option key={c.id} value={String(c.id)}>
                  {c.nombre}
                </option>
              ))}
            </select>
          </label>
          <label className="filter-field">
            Tope de puntos (mapa)
            <select
              value={mapLimite}
              onChange={(e) => setMapLimite(normalizeMapLimite(e.target.value))}
            >
              {MAP_LIMITE_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          <p
            className="muted small filter-help"
            style={{
              gridColumn: '1 / -1',
              margin: 0,
              color: Number(mapLimite) >= 20_000 ? '#9a3412' : undefined,
            }}
          >
            {mapLimiteHelpText(mapLimite)}
          </p>
          <div className="filter-actions">
            <button
              type="button"
              className="btn btn-primary"
              onClick={() => void loadMap()}
              disabled={mapLoading || !desde || !hasta}
            >
              {mapLoading ? 'Actualizando mapa…' : 'Aplicar al mapa'}
            </button>
          </div>
        </div>
      </div>

      {err && <p className="form-error landing-map-form-error">{err}</p>}

      <div className="landing-map-inner">
        {meta && (
          <p className="landing-map-meta muted small">
            En este periodo hay{' '}
            <strong>{meta?.total_con_coordenadas_en_rango?.toLocaleString('es-CO')}</strong> incidentes con coordenadas.
            {meta?.sin_limite_solicitado ? (
              <>
                {' '}
                Modo <strong>sin límite práctico</strong>: el servidor puede devolver hasta{' '}
                <strong>{meta?.tope_absoluto_sin_limite?.toLocaleString('es-CO')}</strong> filas (las más recientes
                primero). En pantalla hay <strong>{meta?.puntos_devueltos?.toLocaleString('es-CO')}</strong>.
                {meta?.recorte_por_tope_absoluto ? (
                  <>
                    {' '}
                    El periodo supera ese tope de seguridad; no se muestran todos los puntos existentes.
                  </>
                ) : null}
              </>
            ) : (
              <>
                {' '}
                El mapa usa un tope de muestra de <strong>{meta?.limite?.toLocaleString('es-CO')}</strong> puntos (del
                más reciente al más antiguo). En pantalla hay{' '}
                <strong>{meta?.puntos_devueltos?.toLocaleString('es-CO')}</strong>
                {meta?.muestra_truncada ? (
                  <>, es decir llegaste al tope y quedan más incidentes sin dibujar.</>
                ) : (
                  <>, es decir se muestran todos los incidentes con coordenadas en este rango respecto a ese tope.</>
                )}
              </>
            )}{' '}
            Periodo: {meta?.fecha_inicio} → {meta?.fecha_fin}. Filtros en servidor: comuna{' '}
            <strong>
              {meta?.filtros?.comuna_id == null ? 'todas' : String(meta.filtros.comuna_id)}
            </strong>
            , barrio{' '}
            <strong>
              {meta?.filtros?.barrio_id == null ? 'todos' : String(meta.filtros.barrio_id)}
            </strong>
            , clase{' '}
            <strong>
              {meta?.filtros?.clase_incidente_id == null
                ? 'todas'
                : String(meta.filtros.clase_incidente_id)}
            </strong>
            . La capa de <strong>calor</strong> resume densidad; los <strong>clusters</strong> permiten acercar y abrir
            detalle (radicado, fecha, clase).
          </p>
        )}

        <div className="landing-map-view-wrap">
          {mapLoading && (
            <div className="landing-map-refresh-overlay muted small" role="status">
              Actualizando…
            </div>
          )}

          {!puntos.length && !mapLoading ? (
            <div className="landing-map-shell landing-map-empty muted" role="status">
              No hay incidentes con coordenadas para estos filtros. Pruebe otro periodo o quite filtros territoriales.
            </div>
          ) : puntos.length > 0 ? (
            <div className="landing-map-shell" aria-label="Mapa de concentración de incidentes">
              <MapContainer
                key={mapInstanceKey}
                center={DEFAULT_CENTER}
                zoom={12}
                className="landing-map-leaflet"
                style={{ height: '100%', width: '100%' }}
                scrollWheelZoom={false}
              >
                <MapResizeEffects compact={compact} />
                <MapBoundsEffect puntos={puntos} />
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <ClusterHeatLayers puntos={puntos} compact={compact} />
              </MapContainer>
            </div>
          ) : null}
        </div>
      </div>
    </>
  )
}
