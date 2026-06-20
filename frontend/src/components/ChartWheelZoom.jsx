import { TransformComponent, TransformWrapper } from 'react-zoom-pan-pinch'

/** Incremento por notch de rueda; más bajo = zoom más suave. */
const WHEEL_ZOOM_STEP = 0.011

/** Incremento de los botones + / −. */
const BUTTON_ZOOM_STEP = 0.12

function ChartWheelZoomToolbar({ resetTransform, zoomIn, zoomOut }) {
  return (
    <div className="chart-wheel-zoom-toolbar">
      <span className="muted small chart-wheel-zoom-hint">
        <span className="chart-wheel-zoom-hint-full">
          Rueda del mouse sobre el gráfico para acercar o alejar · arrastre para mover
        </span>
        <span className="chart-wheel-zoom-hint-compact">Pellizcar o arrastrar para zoom</span>
      </span>
      <div className="chart-wheel-zoom-actions">
        <button type="button" className="chart-zoom-reset" onClick={() => zoomOut(BUTTON_ZOOM_STEP)} aria-label="Alejar">
          −
        </button>
        <button type="button" className="chart-zoom-reset" onClick={() => zoomIn(BUTTON_ZOOM_STEP)} aria-label="Acercar">
          +
        </button>
        <button type="button" className="chart-zoom-reset" onClick={() => resetTransform()} aria-label="Restablecer zoom">
          Restablecer
        </button>
      </div>
    </div>
  )
}

/**
 * Zoom visual con rueda del mouse (como acercar una imagen). No cambia datos ni filtros de fechas.
 */
export function ChartWheelZoom({ children, height = 340, className = '' }) {
  const h = Number(height) || 340

  return (
    <div className={`chart-wheel-zoom ${className}`.trim()}>
      <TransformWrapper
        initialScale={1}
        minScale={1}
        maxScale={8}
        centerOnInit
        smooth
        wheel={{ step: WHEEL_ZOOM_STEP }}
        pinch={{ step: 0.04 }}
        doubleClick={{ disabled: true }}
        panning={{ velocityDisabled: true }}
        limitToBounds={false}
        zoomAnimation={{ animationTime: 180, animationType: 'easeOut' }}
      >
        {({ resetTransform, zoomIn, zoomOut }) => (
          <>
            <ChartWheelZoomToolbar resetTransform={resetTransform} zoomIn={zoomIn} zoomOut={zoomOut} />
            <TransformComponent
              wrapperClass="chart-wheel-zoom-wrap"
              contentClass="chart-wheel-zoom-content"
              wrapperStyle={{ width: '100%', height: `${h}px` }}
              contentStyle={{ width: '100%', height: `${h}px` }}
            >
              {children}
            </TransformComponent>
          </>
        )}
      </TransformWrapper>
    </div>
  )
}
