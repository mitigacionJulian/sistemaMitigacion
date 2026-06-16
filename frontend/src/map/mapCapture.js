import html2canvas from 'html2canvas'

const CAPTURE_CLASS = 'landing-map-shell--capture'

const TRANSIENT_MAP_UI_QUERY =
  '.leaflet-popup, .leaflet-tooltip:not(.landing-map-cell-id-tooltip):not(.landing-map-cell-rank-tooltip)'

function dismissTransientMapUi(root) {
  if (!root) return
  root.querySelectorAll(TRANSIENT_MAP_UI_QUERY).forEach((node) => {
    node.style.setProperty('display', 'none', 'important')
  })
  root.querySelectorAll('.landing-map-refresh-overlay').forEach((node) => {
    node.style.setProperty('display', 'none', 'important')
  })
}

function restoreTransientMapUi(root) {
  if (!root) return
  root.querySelectorAll(TRANSIENT_MAP_UI_QUERY).forEach((node) => {
    node.style.removeProperty('display')
  })
  root.querySelectorAll('.landing-map-refresh-overlay').forEach((node) => {
    node.style.removeProperty('display')
  })
}

function prepareShellForCapture(el) {
  const prev = {
    height: el.style.height,
    minHeight: el.style.minHeight,
    overflow: el.style.overflow,
    contain: el.style.contain,
  }

  el.classList.add(CAPTURE_CLASS)
  el.style.overflow = 'visible'
  el.style.contain = 'none'

  const legend = el.querySelector('.landing-map-legend-card')
  if (legend) {
    const shellRect = el.getBoundingClientRect()
    const legendRect = legend.getBoundingClientRect()
    const extraBottom = Math.ceil(legendRect.bottom - shellRect.bottom + 16)
    if (extraBottom > 0) {
      const nextHeight = el.offsetHeight + extraBottom
      el.style.height = `${nextHeight}px`
      el.style.minHeight = `${nextHeight}px`
    }
  }

  return () => {
    el.classList.remove(CAPTURE_CLASS)
    el.style.height = prev.height
    el.style.minHeight = prev.minHeight
    el.style.overflow = prev.overflow
    el.style.contain = prev.contain
  }
}

function tuneClonedShell(clonedShell) {
  if (!clonedShell) return
  clonedShell.style.overflow = 'visible'
  clonedShell.style.contain = 'none'
  dismissTransientMapUi(clonedShell)

  const legend = clonedShell.querySelector('.landing-map-legend-card')
  if (legend) {
    legend.style.bottom = '14px'
    legend.style.right = '12px'
    const shellRect = clonedShell.getBoundingClientRect()
    const legendRect = legend.getBoundingClientRect()
    const extraBottom = Math.ceil(legendRect.bottom - shellRect.bottom + 16)
    if (extraBottom > 0) {
      const nextHeight = clonedShell.offsetHeight + extraBottom
      clonedShell.style.height = `${nextHeight}px`
      clonedShell.style.minHeight = `${nextHeight}px`
    }
  }
}

export function waitForMapPaint() {
  return new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve))
  })
}

function waitForPaint() {
  return waitForMapPaint()
}

/**
 * Captura el contenedor del mapa Leaflet como imagen JPEG (base64 data URL).
 * @param {HTMLElement | string} target — elemento o selector CSS
 * @returns {Promise<string | null>}
 */
export async function captureMapElement(target) {
  const el = typeof target === 'string' ? document.querySelector(target) : target
  if (!el) return null

  dismissTransientMapUi(el)
  const restoreShell = prepareShellForCapture(el)

  try {
    await waitForPaint()

    const canvas = await html2canvas(el, {
      useCORS: true,
      allowTaint: true,
      scale: Math.min(2, window.devicePixelRatio || 1.5),
      logging: false,
      backgroundColor: '#f1f5f9',
      scrollX: 0,
      scrollY: 0,
      width: el.scrollWidth,
      height: el.scrollHeight,
      windowWidth: el.scrollWidth,
      windowHeight: el.scrollHeight,
      ignoreElements: (node) => {
        if (!(node instanceof HTMLElement)) return false
        return node.classList.contains('leaflet-control-container')
      },
      onclone: (clonedDoc) => {
        const id = el.id
        const clonedShell = id ? clonedDoc.getElementById(id) : clonedDoc.body.querySelector(`.${CAPTURE_CLASS}`)
        tuneClonedShell(clonedShell)
      },
    })
    return canvas.toDataURL('image/jpeg', 0.88)
  } catch {
    return null
  } finally {
    restoreShell()
    restoreTransientMapUi(el)
  }
}
