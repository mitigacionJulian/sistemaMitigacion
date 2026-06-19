/** Título visible y número de reporte (usuario o predeterminado). */
export function resolveReporteTitulo(meta = {}) {
  const tituloUsuario = (meta.titulo || '').trim()
  const seccionEtiqueta = meta.seccion_etiqueta || 'Reporte'

  if (meta.titulo_display && meta.numero_reporte) {
    return {
      titulo: tituloUsuario,
      titulo_display: meta.titulo_display,
      numero_reporte: meta.numero_reporte,
    }
  }

  const now = meta.generado_en ? new Date(meta.generado_en) : new Date()
  const pad = (n) => String(n).padStart(2, '0')
  const numero =
    meta.numero_reporte ||
    `SG-${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`
  const titulo_display = tituloUsuario || `Reporte ${seccionEtiqueta} — ${numero}`

  return {
    titulo: tituloUsuario,
    titulo_display,
    numero_reporte: numero,
  }
}
