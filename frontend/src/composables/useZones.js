import { ref } from 'vue'
import { streamAPI } from '../utils/api'

/**
 * Composable for managing zone CRUD operations
 */
export function useZones() {
  const zones = ref([])
  const selectedZone = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const editingZoneId = ref(null)
  const savePending = ref(false)

  let saveTimeout = null

  /**
   * Fetch all zones from the API
   */
  async function fetchZones() {
    loading.value = true
    error.value = null

    try {
      const response = await streamAPI.getZones()
      zones.value = response.data.zones || []

      // Update selectedZone if it exists to keep it in sync
      if (selectedZone.value) {
        const found = zones.value.find(z => z.name === selectedZone.value.name)
        if (found) {
          selectedZone.value = found
        }
      }
    } catch (err) {
      error.value = 'Failed to fetch zones'
      console.error('Error fetching zones:', err)
    } finally {
      loading.value = false
    }
  }

  /**
   * Create a new zone
   * @param {Object} zone - Zone data {name, type, geometry, trigger_classes}
   */
  async function createZone(zone) {
    loading.value = true
    error.value = null

    try {
      await streamAPI.createZone(zone)
      await fetchZones() // Refresh zones list
      return true
    } catch (err) {
      error.value = 'Failed to create zone'
      console.error('Error creating zone:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Update an existing zone
   * @param {string} identifier - Zone name or ID
   * @param {Object} data - Updated zone data
   */
  async function updateZone(identifier, data) {
    loading.value = true
    error.value = null

    try {
      await streamAPI.updateZone(identifier, data)
      await fetchZones()
      return true
    } catch (err) {
      error.value = 'Failed to update zone'
      console.error('Error updating zone:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Delete a zone
   * @param {string} name - Zone name
   */
  async function deleteZone(name) {
    loading.value = true
    error.value = null

    try {
      await streamAPI.deleteZone(name)
      await fetchZones() // Refresh zones list
      if (selectedZone.value?.name === name) {
        selectedZone.value = null
      }
      return true
    } catch (err) {
      error.value = 'Failed to delete zone'
      console.error('Error deleting zone:', err)
      return false
    } finally {
      loading.value = false
    }
  }

  /**
   * Select a zone
   * @param {Object} zone - Zone to select
   */
  function selectZone(zone) {
    selectedZone.value = zone
  }

  /**
   * Deselect the current zone
   */
  function deselectZone() {
    selectedZone.value = null
  }

  /**
   * Find a zone by name
   * @param {string} name - Zone name
   * @returns {Object|null} Zone object or null
   */
  function findZoneByName(name) {
    return zones.value.find(z => z.name === name) || null
  }

  /**
   * Start editing a zone
   * @param {string} zoneName - Name of zone to edit
   */
  function startEditingZone(zoneName) {
    editingZoneId.value = zoneName
    selectedZone.value = zones.value.find(z => z.name === zoneName)
  }

  /**
   * Stop editing and auto-save if needed
   */
  function stopEditingZone() {
    if (saveTimeout) {
      clearTimeout(saveTimeout)
    }

    if (savePending.value && selectedZone.value) {
      // Use ID if available, otherwise fallback to the original name stored in editingZoneId
      const identifier = selectedZone.value.id || editingZoneId.value
      updateZone(identifier, selectedZone.value)
    }

    editingZoneId.value = null
    selectedZone.value = null
    savePending.value = false
  }

  /**
   * Schedule auto-save with debounce
   * @param {Object} zone - Zone object to save
   */
  function scheduleAutoSave(zone) {
    if (saveTimeout) {
      clearTimeout(saveTimeout)
    }

    savePending.value = true
    saveTimeout = setTimeout(() => {
      // Use ID if available, otherwise fallback to the original name stored in editingZoneId
      // Note: This assumes we are auto-saving the currently edited zone.
      const identifier = zone.id || editingZoneId.value
      updateZone(identifier, zone)
      savePending.value = false
    }, 500)
  }

  return {
    // State
    zones,
    selectedZone,
    loading,
    error,
    editingZoneId,
    savePending,

    // Methods
    fetchZones,
    createZone,
    updateZone,
    deleteZone,
    selectZone,
    deselectZone,
    findZoneByName,
    startEditingZone,
    stopEditingZone,
    scheduleAutoSave
  }
}
