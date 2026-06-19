const FILTER_LABELS = {
  desde: 'Desde',
  hasta: 'Hasta',
  comuna: 'Comuna',
  comuna_id: 'Comuna',
  barrio: 'Barrio',
  barrio_id: 'Barrio',
  clase_incidente: 'Clase de incidente',
  clase_incidente_id: 'Clase de incidente',
  territorio: 'Territorio',
  top_n: 'Top N',
  horizonte_meses: 'Horizonte (meses)',
  modelo_proyeccion: 'Modelo proyección mensual',
  modelo_proporcion: 'Modelo proporción fatales',
  modelo_carga: 'Modelo carga / patrones',
  variable: 'Variable proyectada',
  nivel_prioridad: 'Nivel prioridad',
  nivel_carga: 'Nivel carga esperada',
  excluir_covid: 'Excluir meses COVID',
  desglose_clase: 'Desglose por clase',
  desglose_comuna: 'Desglose por comuna',
  consultas_incluidas: 'Consultas incluidas',
  modo: 'Modo del asistente',
  ventana_ma: 'Ventana media móvil',
}

export function filtrosReporteEntries(filtros = {}) {
  return Object.entries(filtros).filter(([, value]) => value !== undefined && value !== null && value !== '')
}

export function labelFiltroReporte(key) {
  return FILTER_LABELS[key] || key.replace(/_/g, ' ')
}

export function formatFiltroValor(value) {
  if (typeof value === 'boolean') return value ? 'Sí' : 'No'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}
