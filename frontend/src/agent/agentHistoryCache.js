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

export function clearAgentHistory() {
  localStorage.removeItem(STORAGE_KEY)
}
