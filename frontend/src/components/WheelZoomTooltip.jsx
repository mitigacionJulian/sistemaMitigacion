import { createPortal } from 'react-dom'

const mouse = { x: 0, y: 0 }

if (typeof window !== 'undefined') {
  window.addEventListener(
    'mousemove',
    (e) => {
      mouse.x = e.clientX
      mouse.y = e.clientY
    },
    { passive: true },
  )
}

const defaultFormatter = (value, name) => {
  if (value == null) return ['—', name]
  if (typeof value === 'number') return [value.toLocaleString('es-CO'), name]
  return [value, name]
}

/**
 * Tooltip de Recharts renderizado en portal con posición fija (no escala con el zoom del gráfico).
 */
export function WheelZoomTooltip({
  active,
  payload,
  label,
  formatter = defaultFormatter,
  labelFormatter,
  separator = ' : ',
}) {
  if (!active || !payload?.length) return null

  const displayLabel = labelFormatter ? labelFormatter(label, payload) : label
  const offsetX = 14
  const offsetY = 14
  const left = mouse.x + offsetX
  const top = mouse.y + offsetY

  const items = payload.filter((entry) => entry.value != null && entry.type !== 'none')

  const body = (
    <div
      className="wheel-zoom-tooltip"
      style={{ left: `${left}px`, top: `${top}px` }}
      role="tooltip"
    >
      {displayLabel != null && displayLabel !== '' && (
        <p className="wheel-zoom-tooltip-label">{displayLabel}</p>
      )}
      <ul className="wheel-zoom-tooltip-list">
        {items.map((entry, i) => {
          const formatted = formatter(entry.value, entry.name, entry, i, payload)
          const [val, name] = Array.isArray(formatted) ? formatted : [formatted, entry.name]
          return (
            <li key={`${entry.dataKey ?? entry.name}-${i}`} style={{ color: entry.color }}>
              {name != null && name !== '' ? (
                <>
                  <span className="wheel-zoom-tooltip-name">{name}</span>
                  {separator}
                  <span className="wheel-zoom-tooltip-value">{val}</span>
                </>
              ) : (
                <span className="wheel-zoom-tooltip-value">{val}</span>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )

  return createPortal(body, document.body)
}

/** Props compartidas para ocultar el wrapper nativo de Recharts (el contenido va al portal). */
export const wheelZoomTooltipProps = {
  cursor: false,
  isAnimationActive: false,
  wrapperStyle: { visibility: 'hidden', pointerEvents: 'none' },
}
