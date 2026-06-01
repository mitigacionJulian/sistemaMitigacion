const DEFAULT_COLS = [
  'id',
  'latitud',
  'longitud',
  'radicado',
  'fecha_incidente',
  'clase_incidente',
]

self.onmessage = (ev) => {
  const { id, data } = ev.data || {}
  try {
    if (!data?.puntos?.length || data.meta?.formato_puntos !== 'compacto') {
      self.postMessage({ id, data })
      return
    }
    const cols = data.meta.columnas_puntos || DEFAULT_COLS
    const idx = Object.fromEntries(cols.map((c, i) => [c, i]))
    const puntos = data.puntos.map((row) => ({
      id: row[idx.id],
      latitud: row[idx.latitud],
      longitud: row[idx.longitud],
      radicado: row[idx.radicado],
      fecha_incidente: row[idx.fecha_incidente],
      clase_incidente: row[idx.clase_incidente] ?? '',
    }))
    self.postMessage({ id, data: { ...data, puntos } })
  } catch (err) {
    self.postMessage({ id, error: err instanceof Error ? err.message : String(err) })
  }
}
