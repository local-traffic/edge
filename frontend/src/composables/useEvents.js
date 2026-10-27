import { ref, onUnmounted } from 'vue'
import { streamAPI } from '../utils/api'

/**
 * Composable for managing real-time detection events via SSE
 */
export function useEvents(maxEvents = 50) {
  const events = ref([])
  const connected = ref(false)
  const error = ref(null)
  let eventSource = null

  /**
   * Fetch initial event history from the API
   */
  async function fetchHistory() {
    try {
      const response = await streamAPI.getEvents(maxEvents)
      events.value = response.data.events || []
      error.value = null
    } catch (err) {
      error.value = 'Failed to fetch event history'
      console.error('Error fetching events:', err)
    }
  }

  /**
   * Connect to SSE stream for real-time events
   */
  function connect() {
    if (eventSource) return

    const streamUrl = streamAPI.getEventsStreamUrl()
    eventSource = new EventSource(streamUrl)

    eventSource.onopen = () => {
      connected.value = true
      error.value = null
    }

    eventSource.onmessage = (event) => {
      try {
        const eventData = JSON.parse(event.data)
        events.value = [eventData, ...events.value.slice(0, maxEvents - 1)]
      } catch (err) {
        console.error('Error parsing SSE event:', err)
      }
    }

    eventSource.onerror = () => {
      connected.value = false
      error.value = 'Connection lost, reconnecting...'

      eventSource.close()
      eventSource = null

      setTimeout(() => {
        if (!eventSource) {
          connect()
        }
      }, 3000)
    }
  }

  /**
   * Disconnect from SSE stream
   */
  function disconnect() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
      connected.value = false
    }
  }

  /**
   * Start listening for events (fetch history + connect to SSE)
   */
  async function start() {
    await fetchHistory()
    connect()
  }

  /**
   * Stop listening for events
   */
  function stop() {
    disconnect()
  }

  /**
   * Clear all events
   */
  function clear() {
    events.value = []
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    events,
    connected,
    error,
    start,
    stop,
    clear,
    fetchHistory
  }
}
