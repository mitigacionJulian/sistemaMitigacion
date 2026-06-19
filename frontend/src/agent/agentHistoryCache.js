import { APP_NAME_SHORT } from '../config/brand.js'

const STORAGE_KEY = 'sg_agent_history_v1'
const MAX_ENTRIES = 80

function normalizeQuestion(text) {
  return (text || '').trim().toLowerCase().replace(/\s+/g, ' ')
}

function scopeSuffix(analyst) {
  return analyst ? '|analyst' : '|public'
}

function readStore() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { entries: [] }
    const parsed = JSON.parse(raw)
    if (!parsed || !Array.isArray(parsed.entries)) return { entries: [] }
    return parsed
  } catch {
    return { entries: [] }
  }
}

function writeStore(store) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(store))
  } catch {
    /* quota exceeded — ignorar */
  }
}

export function findCachedAnswer(question, { analyst = false } = {}) {
  const norm = normalizeQuestion(question) + scopeSuffix(analyst)
  if (!norm) return null
  const store = readStore()
  const hit = store.entries.find((e) => e.questionNorm === norm)
  return hit || null
}

export function appendHistoryEntry({ question, answer, model, fromCache, analyst = false, meta = {} }) {
  const norm = normalizeQuestion(question) + scopeSuffix(analyst)
  if (!norm || !answer) return
  const store = readStore()
  const filtered = store.entries.filter((e) => e.questionNorm !== norm)
  filtered.unshift({
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    question,
    questionNorm: norm,
    answer,
    model: model || null,
    fromCache: Boolean(fromCache),
    analyst: Boolean(analyst),
    ts: new Date().toISOString(),
    ...meta,
  })
  writeStore({ entries: filtered.slice(0, MAX_ENTRIES) })
}

export function loadAgentHistory({ analyst = false } = {}) {
  const suffix = scopeSuffix(analyst)
  return readStore().entries.filter((e) => e.questionNorm?.endsWith(suffix))
}

export function countAgentHistory({ analyst = false } = {}) {
  return loadAgentHistory({ analyst }).length
}

export function clearAgentHistory({ analyst } = {}) {
  if (analyst === undefined) {
    localStorage.removeItem(STORAGE_KEY)
    return
  }
  const suffix = scopeSuffix(analyst)
  const store = readStore()
  writeStore({ entries: store.entries.filter((e) => !e.questionNorm?.endsWith(suffix)) })
}

function formatReportTimestamp(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' })
  } catch {
    return iso
  }
}

export function buildAgentHistoryReport({ analyst = false } = {}) {
  const entries = loadAgentHistory({ analyst })
  const modo = analyst ? 'Analista (histórico + predicciones)' : 'Público (solo histórico)'
  const lines = [
    `Reporte de consultas — Asistente de accidentalidad (${APP_NAME_SHORT})`,
    `Generado: ${formatReportTimestamp(new Date().toISOString())}`,
    `Modo: ${modo}`,
    `Total de consultas guardadas: ${entries.length}`,
    '',
    'Nota: solo incluye preguntas respondidas y almacenadas en caché local del navegador.',
    '',
    '═'.repeat(72),
    '',
  ]
  entries.forEach((entry, index) => {
    const n = entries.length - index
    lines.push(`Consulta ${n}`)
    lines.push(`Fecha: ${formatReportTimestamp(entry.ts)}`)
    lines.push(`Pregunta: ${entry.question}`)
    lines.push('')
    lines.push(`Respuesta: ${entry.answer}`)
    lines.push('')
    if (entry.model) lines.push(`Modelo: ${entry.model}`)
    if (entry.fromCache) lines.push('Origen: respuesta recuperada de caché')
    lines.push('')
    lines.push('─'.repeat(72))
    lines.push('')
  })
  return lines.join('\n')
}

export function downloadAgentHistoryReport({ analyst = false } = {}) {
  const text = buildAgentHistoryReport({ analyst })
  const blob = new Blob([text], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const suffix = analyst ? 'analista' : 'publico'
  const stamp = new Date().toISOString().slice(0, 10)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = `asistente-consultas-${suffix}-${stamp}.txt`
  anchor.click()
  URL.revokeObjectURL(url)
}
