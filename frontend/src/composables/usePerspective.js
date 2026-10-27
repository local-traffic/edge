import { ref } from 'vue'
import { streamAPI } from '../utils/api'

export function usePerspective() {
  // Default corner positions (normalized 0-1)
  const defaultCorners = [
    { x: 0.25, y: 0.25 },  // Top-left
    { x: 0.75, y: 0.25 },  // Top-right
    { x: 0.75, y: 0.75 },  // Bottom-right
    { x: 0.25, y: 0.75 }   // Bottom-left
  ]

  const defaultEdgeLengths = {
    top: 10.0,
    left: 15.0,
    bottom: 10.0
  }

  const corners = ref([...defaultCorners.map(c => ({ ...c }))])
  const edgeLengths = ref({ ...defaultEdgeLengths })
  const loading = ref(false)
  const saving = ref(false)
  const error = ref(null)
  const hasCalibration = ref(false)

  async function fetchPerspective() {
    loading.value = true
    error.value = null

    try {
      const response = await streamAPI.getPerspective()
      const data = response.data

      if (data.enabled && data.perspective) {
        const perspective = data.perspective

        // Load corners
        if (perspective.corners && perspective.corners.length === 4) {
          corners.value = perspective.corners.map(c => ({
            x: c[0],
            y: c[1]
          }))
        }

        // Load edge lengths
        if (perspective.edge_lengths) {
          edgeLengths.value = {
            top: perspective.edge_lengths.top || defaultEdgeLengths.top,
            left: perspective.edge_lengths.left || defaultEdgeLengths.left,
            bottom: perspective.edge_lengths.bottom || defaultEdgeLengths.bottom
          }
        }

        hasCalibration.value = true
      } else {
        hasCalibration.value = false
      }
    } catch (err) {
      console.error('Failed to fetch perspective:', err)
      error.value = 'Failed to load perspective calibration'
    } finally {
      loading.value = false
    }
  }

  async function savePerspective() {
    saving.value = true
    error.value = null

    try {
      const data = {
        corners: corners.value.map(c => [c.x, c.y]),
        edge_lengths: {
          top: edgeLengths.value.top,
          left: edgeLengths.value.left,
          bottom: edgeLengths.value.bottom
        }
      }

      await streamAPI.savePerspective(data)
      hasCalibration.value = true
      return true
    } catch (err) {
      console.error('Failed to save perspective:', err)
      error.value = 'Failed to save perspective calibration'
      return false
    } finally {
      saving.value = false
    }
  }

  async function deletePerspective() {
    saving.value = true
    error.value = null

    try {
      await streamAPI.deletePerspective()
      hasCalibration.value = false
      resetToDefault()
      return true
    } catch (err) {
      console.error('Failed to delete perspective:', err)
      error.value = 'Failed to delete perspective calibration'
      return false
    } finally {
      saving.value = false
    }
  }

  function resetToDefault() {
    corners.value = [...defaultCorners.map(c => ({ ...c }))]
    edgeLengths.value = { ...defaultEdgeLengths }
  }

  function updateCorner(index, point) {
    if (index >= 0 && index < 4) {
      // Allow values outside 0-1 range for corners outside video area
      corners.value[index] = {
        x: point.x,
        y: point.y
      }
    }
  }

  return {
    corners,
    edgeLengths,
    loading,
    saving,
    error,
    hasCalibration,
    fetchPerspective,
    savePerspective,
    deletePerspective,
    resetToDefault,
    updateCorner
  }
}
