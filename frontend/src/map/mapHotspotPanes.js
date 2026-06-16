export const HOTSPOTS_GRID_PANE = 'hotspots-grid-pane'
export const HOTSPOTS_OUTLINE_PANE = 'hotspots-outline-pane'
export const HOTSPOTS_LABEL_PANE = 'hotspots-label-pane'

/** @typedef {'inactive' | 'draw' | 'adjust'} AreaEditorPhase */

export function ensureHotspotsGridPane(map) {
  if (!map.getPane(HOTSPOTS_GRID_PANE)) {
    map.createPane(HOTSPOTS_GRID_PANE)
    const pane = map.getPane(HOTSPOTS_GRID_PANE)
    pane.style.zIndex = '560'
    pane.style.pointerEvents = 'auto'
  }
  return HOTSPOTS_GRID_PANE
}

export function ensureHotspotsOutlinePane(map) {
  if (!map.getPane(HOTSPOTS_OUTLINE_PANE)) {
    map.createPane(HOTSPOTS_OUTLINE_PANE)
    const pane = map.getPane(HOTSPOTS_OUTLINE_PANE)
    pane.style.zIndex = '565'
    // Solo referencia visual: no interceptar hover/clic de la cuadrícula.
    pane.style.pointerEvents = 'none'
  }
  return HOTSPOTS_OUTLINE_PANE
}

export function ensureHotspotsLabelPane(map) {
  if (!map.getPane(HOTSPOTS_LABEL_PANE)) {
    map.createPane(HOTSPOTS_LABEL_PANE)
    const pane = map.getPane(HOTSPOTS_LABEL_PANE)
    pane.style.zIndex = '562'
    pane.style.pointerEvents = 'none'
  }
  return HOTSPOTS_LABEL_PANE
}

/** Habilita o bloquea interacción en la cuadrícula P14 (p. ej. mientras se dibuja el área). */
export function setHotspotPanesInteractive(map, interactive) {
  const gridPane = map.getPane(HOTSPOTS_GRID_PANE)
  if (gridPane) {
    gridPane.style.pointerEvents = interactive ? 'auto' : 'none'
  }
}
