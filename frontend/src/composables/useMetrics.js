import { ref, onUnmounted } from 'vue'
import { streamAPI } from '../utils/api'

/**
 * Default metrics structure matching backend FrameTimingMetrics
 */
export const DEFAULT_METRICS = {
  fps: 0,
  inference_ms: 0,
  tracking_ms: 0,
  motion_detection_ms: 0,
  zones_ms: 0,
  annotation_ms: 0,
  total_pipeline_ms: 0,
  timestamp: null
}

/**
 * Composable for managing performance metrics polling
 */
export function useMetrics() {
  const metrics = ref({ ...DEFAULT_METRICS })
  const polling = ref(false)
  const error = ref(null)
  let intervalId = null

  /**
   * Fetch metrics from the API
   */
  async function fetchMetrics() {
    try {
      const response = await streamAPI.getMetrics()
      metrics.value = {
        ...metrics.value,
        ...response.data
      }
      error.value = null
    } catch (err) {
      error.value = 'Failed to fetch metrics'
      console.error('Error fetching metrics:', err)
    }
  }

  /**
   * Start polling for metrics
   * @param {number} interval - Polling interval in milliseconds (default 500ms)
   */
  function startPolling(interval = 500) {
    if (polling.value) return

    polling.value = true
    fetchMetrics() // Fetch immediately

    intervalId = setInterval(() => {
      fetchMetrics()
    }, interval)
  }

  /**
   * Stop polling for metrics
   */
  function stopPolling() {
    if (!polling.value) return

    polling.value = false
    if (intervalId !== null) {
      clearInterval(intervalId)
      intervalId = null
    }
  }

  /**
   * Reset metrics to default values
   */
  function resetMetrics() {
    metrics.value = { ...DEFAULT_METRICS }
  }

  // Cleanup on component unmount
  onUnmounted(() => {
    stopPolling()
  })

  return {
    // State
    metrics,
    polling,
    error,

    // Methods
    fetchMetrics,
    startPolling,
    stopPolling,
    resetMetrics
  }
}
