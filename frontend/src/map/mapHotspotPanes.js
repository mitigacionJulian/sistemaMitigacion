export const HOTSPOTS_GRID_PANE = 'hotspots-grid-pane'
export const HOTSPOTS_OUTLINE_PANE = 'hotspots-outline-pane'

/** @typedef {'inactive' | 'draw' | 'adjust'} AreaEditorPhase */

export function ensureHotspotsGridPane(map) {
  if (!map.getPane(HOTSPOTS_GRID_PANE)) {
    map.createPane(HOTSPOTS_GRID_PANE)
    map.getPane(HOTSPOTS_GRID_PANE).style.zIndex = '560'
  }
  return HOTSPOTS_GRID_PANE
}

export function ensureHotspotsOutlinePane(map) {
  if (!map.getPane(HOTSPOTS_OUTLINE_PANE)) {
    map.createPane(HOTSPOTS_OUTLINE_PANE)
    map.getPane(HOTSPOTS_OUTLINE_PANE).style.zIndex = '565'
  }
  return HOTSPOTS_OUTLINE_PANE
}

/** Deja pasar clics al editor de área (z-index 550) mientras se dibuja. */
export function setHotspotPanesInteractive(map, interactive) {
  for (const name of [HOTSPOTS_GRID_PANE, HOTSPOTS_OUTLINE_PANE]) {
    const pane = map.getPane(name)
    if (pane) pane.style.pointerEvents = interactive ? '' : 'none'
  }
}
