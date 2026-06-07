import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchAgentChat, fetchAgentInfo } from '../api/agentClient.js'
import {
  appendHistoryEntry,
  findCachedAnswer,
  loadAgentHistory,
} from '../agent/agentHistoryCache.js'
import { useAuth } from '../context/AuthContext.jsx'

const SUGGESTIONS_PUBLIC = [
  '¿Cuántos incidentes hubo el último año con datos?',
  '¿Qué comunas concentran más víctimas?',
  '¿Cómo se distribuyen los incidentes por día de la semana?',
  '¿Cuál es la evolución mensual de incidentes fatales?',
]

const SUGGESTIONS_ANALYST = [
  'De los próximos 6 meses, ¿cuál tiende a aumentar los incidentes y en qué sector?',
  '¿Qué comunas tienen mayor prioridad territorial proyectada?',
  '¿Cuál es la carga esperada por comuna en el horizonte de 3 meses?',
]

function formatModelLabel(modelUsed, fallback) {
  if (!modelUsed) return fallback || '—'
  if (modelUsed.includes('lite')) return 'Flash-Lite'
  if (modelUsed.includes('flash')) return 'Flash'
  return modelUsed
}

export function Agente() {
  const { isAnalista } = useAuth()
  const [info, setInfo] = useState(null)
  const [infoError, setInfoError] = useState('')
  const [model, setModel] = useState('flash')
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [quota, setQuota] = useState(null)
  const listRef = useRef(null)

  const predictionsEnabled = Boolean(info?.predictions_enabled ?? isAnalista)
  const suggestions = predictionsEnabled ? SUGGESTIONS_ANALYST : SUGGESTIONS_PUBLIC

  useEffect(() => {
    let cancelled = false
    fetchAgentInfo()
      .then((data) => {
        if (!cancelled) setInfo(data)
      })
      .catch((err) => {
        if (!cancelled) setInfoError(err.message)
      })
    return () => {
      cancelled = true
    }
  }, [isAnalista])

  useEffect(() => {
    const history = loadAgentHistory({ analyst: predictionsEnabled })
    if (history.length === 0) return
    const restored = []
    for (let i = history.length - 1; i >= 0; i -= 1) {
      const entry = history[i]
      restored.push({ role: 'user', content: entry.question, meta: { restored: true } })
      restored.push({
        role: 'assistant',
        content: entry.answer,
        meta: {
          fromCache: entry.fromCache,
          model: entry.model,
          restored: true,
        },
      })
    }
    setMessages(restored.slice(-12))
  }, [predictionsEnabled])

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight
    }
  }, [messages, loading])

  const sendMessage = useCallback(
    async (rawText) => {
      const text = (rawText || '').trim()
      if (!text || loading) return

      setError('')
      setInput('')
      const userMsg = { role: 'user', content: text }
      setMessages((prev) => [...prev, userMsg])
      setLoading(true)

      const localHit = findCachedAnswer(text, { analyst: predictionsEnabled })
      if (localHit) {
        const assistantMsg = {
          role: 'assistant',
          content: localHit.answer,
          meta: {
            fromCache: true,
            cacheSource: 'local',
            model: localHit.model,
          },
        }
        setMessages((prev) => [...prev, assistantMsg])
        setLoading(false)
        return
      }

      try {
        const history = messages
          .filter((m) => m.role === 'user' || m.role === 'assistant')
          .slice(-8)
          .map((m) => ({ role: m.role, content: m.content }))

        const result = await fetchAgentChat({ message: text, model, history })
        const assistantMsg = {
          role: 'assistant',
          content: result.answer,
          meta: {
            fromCache: result.from_cache,
            cacheSource: result.from_cache ? 'server' : null,
            model: result.model_used,
            fallbackUsed: result.fallback_used,
            toolsUsed: result.tools_used,
          },
        }
        setMessages((prev) => [...prev, assistantMsg])
        if (result.quota) setQuota(result.quota)

        appendHistoryEntry({
          question: text,
          answer: result.answer,
          model: result.model_used,
          fromCache: result.from_cache,
          analyst: predictionsEnabled,
          meta: { fallbackUsed: result.fallback_used },
        })
      } catch (err) {
        setError(err.message)
        setMessages((prev) => prev.slice(0, -1))
        setInput(text)
      } finally {
        setLoading(false)
      }
    },
    [loading, messages, model, predictionsEnabled],
  )

  const handleSubmit = (e) => {
    e.preventDefault()
    void sendMessage(input)
  }

  const disclaimer = info?.disclaimer

  return (
    <section className="agent-page">
      <header className="agent-header">
        <p className="eyebrow">Consulta en lenguaje natural</p>
        <h1>Asistente de accidentalidad</h1>
        <p className="lead">
          Pregunta sobre incidentes en Medellín. Consulta datos históricos sin iniciar sesión.
          {predictionsEnabled
            ? ' Con su sesión de analista también puede consultar predicciones y proyecciones.'
            : ' Para predicciones, inicie sesión como analista.'}
        </p>
      </header>

      {predictionsEnabled && (
        <p className="agent-analyst-badge panel muted">
          Sesión de analista activa — predicciones habilitadas en este asistente.
        </p>
      )}

      {!predictionsEnabled && (
        <p className="agent-login-hint panel muted">
          ¿Necesita proyecciones? <Link to="/login">Inicie sesión</Link> con una cuenta de analista.
        </p>
      )}

      <aside className="agent-notice panel" role="note" aria-label="Avisos del asistente">
        <h2 className="agent-notice-title">Avisos importantes</h2>
        {infoError && <p className="form-error">{infoError}</p>}
        {disclaimer ? (
          <ul className="agent-notice-list">
            <li>
              <strong>Límite de consultas:</strong> {disclaimer.quota}
            </li>
            <li>
              <strong>Política de Google:</strong> {disclaimer.privacy}
            </li>
            <li>
              <strong>Alcance:</strong> {disclaimer.scope}
            </li>
          </ul>
        ) : (
          !infoError && <p className="muted">Cargando avisos…</p>
        )}
        {quota?.limit > 0 && (
          <p className="agent-quota muted">
            Consultas hoy desde esta red: {quota.used} / {quota.limit}
            {quota.remaining != null ? ` (${quota.remaining} restantes)` : ''}
          </p>
        )}
      </aside>

      <div className="agent-controls panel">
        <label className="agent-model-label" htmlFor="agent-model">
          Modelo Gemini
        </label>
        <div className="agent-model-row">
          <select
            id="agent-model"
            className="input"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            disabled={loading}
          >
            <option value="flash">2.5 Flash — equilibrio calidad / cuota</option>
            <option value="flash-lite">2.5 Flash-Lite — más consultas</option>
          </select>
          <span className="muted agent-model-hint">
            Si un modelo agota su cuota, se usará automáticamente el otro.
          </span>
        </div>
      </div>

      <div className="agent-chat panel">
        <div className="agent-messages" ref={listRef} aria-live="polite">
          {messages.length === 0 && (
            <div className="agent-empty">
              <p className="muted">Ejemplos de preguntas:</p>
              <ul className="agent-suggestions">
                {suggestions.map((s) => (
                  <li key={s}>
                    <button type="button" className="btn btn-ghost agent-suggestion" onClick={() => sendMessage(s)}>
                      {s}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {messages.map((msg, idx) => (
            <div
              key={`${idx}-${msg.content.slice(0, 24)}`}
              className={`agent-bubble agent-bubble--${msg.role}`}
            >
              <p className="agent-bubble-text">{msg.content}</p>
              {msg.role === 'assistant' && msg.meta && (
                <p className="agent-bubble-meta muted">
                  {msg.meta.fromCache && (
                    <span className="agent-tag">
                      Caché {msg.meta.cacheSource === 'local' ? 'local' : 'servidor'}
                    </span>
                  )}
                  {msg.meta.model && (
                    <span className="agent-tag">{formatModelLabel(msg.meta.model, model)}</span>
                  )}
                  {msg.meta.fallbackUsed && (
                    <span className="agent-tag">Modelo alternativo</span>
                  )}
                </p>
              )}
            </div>
          ))}
          {loading && (
            <div className="agent-bubble agent-bubble--assistant agent-bubble--loading">
              <p className="muted">Consultando datos…</p>
            </div>
          )}
        </div>

        {error && <p className="form-error agent-error">{error}</p>}

        <form className="agent-form" onSubmit={handleSubmit}>
          <textarea
            className="input agent-input"
            rows={3}
            placeholder="Escribe tu pregunta sobre incidentes en Medellín…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            maxLength={2000}
          />
          <div className="agent-form-actions">
            <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>
              {loading ? 'Enviando…' : 'Enviar'}
            </button>
          </div>
        </form>
      </div>
    </section>
  )
}
