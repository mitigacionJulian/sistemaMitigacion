import { APP_NAME } from '../../config/brand.js'
import { resolveReporteTitulo } from './reporteTitulo.js'

export function buildAsistenteReporte({
  titulo = '',
  notas = '',
  filtros = {},
  entries = [],
  user = null,
  isAnalista = false,
}) {
  const generadoEn = new Date().toISOString()
  const seccionEtiqueta = 'Asistente de accidentalidad'
  const { titulo: tituloLimpio, titulo_display, numero_reporte } = resolveReporteTitulo({
    titulo,
    seccion_etiqueta: seccionEtiqueta,
    generado_en: generadoEn,
  })

  const usuario = user?.first_name
    ? `${user.first_name}${user.last_name ? ` ${user.last_name}` : ''}`.trim()
    : user?.username || 'Visitante'

  return {
    meta: {
      usuario,
      username: user?.username || '',
      email: user?.email || '',
      rol: isAnalista ? 'Analista' : 'Público',
      rol_codigo: isAnalista ? 'analista' : 'publico',
      generado_en: generadoEn,
      seccion: 'asistente',
      seccion_etiqueta: seccionEtiqueta,
      filtros,
      titulo: tituloLimpio,
      titulo_display,
      numero_reporte,
      notas: (notas || '').trim(),
      sistema: APP_NAME,
    },
    cuerpo: {
      tipo: 'asistente',
      total_consultas: entries.length,
      conversacion: entries.map((entry, index) => ({
        numero: entries.length - index,
        fecha: entry.ts,
        pregunta: entry.question,
        respuesta: entry.answer,
        modelo: entry.model || null,
        from_cache: Boolean(entry.fromCache),
      })),
      interpretacion:
        'Registro de consultas realizadas al asistente en lenguaje natural. ' +
        'Las respuestas provienen de datos históricos depurados y, si aplica, proyecciones modeladas.',
      limitaciones:
        'Solo incluye interacciones almacenadas en caché local del navegador. ' +
        'No sustituye un informe técnico oficial ni establece relaciones causales.',
    },
  }
}
