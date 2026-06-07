import { forwardRef, useEffect, useImperativeHandle, useRef } from 'react'
import { useMap } from 'react-leaflet'
import { DrawAreaSelection } from '@bopen/leaflet-area-selection'
import '@bopen/leaflet-area-selection/dist/index.css'

function geometryFromPolygon(polygon) {
  const gj = polygon.toGeoJSON()
  return JSON.stringify(gj.geometry)
}

/**
 * @typedef {import('./mapHotspotPanes.js').AreaEditorPhase} AreaEditorPhase
 * @typedef {{ clear: () => void, dismissEditor: () => void }} MapAreaSelectionHandle
 */

/**
 * @type {import('react').ForwardRefExoticComponent<{
 *   enabled: boolean
 *   onAreaChange: (geojsonGeometry: string | null) => void
 *   onPhaseChange?: (phase: AreaEditorPhase) => void
 * } & import('react').RefAttributes<MapAreaSelectionHandle>>}
 */
export const MapAreaSelection = forwardRef(function MapAreaSelection(
  { enabled, onAreaChange, onPhaseChange },
  ref,
) {
  const map = useMap()
  const controlRef = useRef(null)
  const onAreaChangeRef = useRef(onAreaChange)
  const onPhaseChangeRef = useRef(onPhaseChange)
  onAreaChangeRef.current = onAreaChange
  onPhaseChangeRef.current = onPhaseChange

  const notifyPhase = (phase) => {
    onPhaseChangeRef.current?.(phase)
  }

  useImperativeHandle(ref, () => ({
    clear() {
      controlRef.current?.deactivate?.()
      map.dragging.enable()
      notifyPhase('inactive')
      onAreaChangeRef.current(null)
    },
    dismissEditor() {
      controlRef.current?.deactivate?.()
      map.dragging.enable()
      notifyPhase('inactive')
    },
  }))

  useEffect(() => {
    if (!enabled) {
      if (controlRef.current) {
        map.removeControl(controlRef.current)
        controlRef.current = null
      }
      map.dragging.enable()
      notifyPhase('inactive')
      onAreaChangeRef.current(null)
      return undefined
    }

    const control = new DrawAreaSelection({
      fadeOnActivation: true,
      onButtonActivate: () => {
        notifyPhase('draw')
      },
      onPolygonReady: (polygon) => {
        notifyPhase('adjust')
        try {
          onAreaChangeRef.current(geometryFromPolygon(polygon))
        } catch {
          /* polígono aún incompleto */
        }
      },
      onButtonDeactivate: () => {
        map.dragging.enable()
        notifyPhase('inactive')
        onAreaChangeRef.current(null)
      },
    })
    map.addControl(control)
    controlRef.current = control
    notifyPhase('inactive')

    return () => {
      map.removeControl(control)
      controlRef.current = null
      map.dragging.enable()
      notifyPhase('inactive')
    }
  }, [map, enabled])

  return null
})
