<template>
  <div class="card">
    <Message v-if="error" severity="error" :closable="false">
      {{ error }}
    </Message>

    <SidebarLayout>
      <template #sidebar>
        <Toolbar
          :active-mode="currentMode"
          @mode-change="handleModeChange"
        />

        <SidebarPanel title="Zones">
          <ZoneList
            :zones="zones"
            :selected-zone="selectedZone"
            :editing-zone-id="editingZoneId"
            @select="handleZoneSelect"
            @delete="handleZoneDelete"
            @edit="handleZoneSelect"
            @update="handleZoneUpdate"
            @stopEdit="handleStopEdit"
          />
        </SidebarPanel>

        <CameraControls
            :active="currentMode === 'af_window'"
            @ret-afwindow="handleSetAFWindow"
            @reset-afwindow="handleResetAFWindow"
          />

        <SaveClipButton />

        <SidebarPanel title="Threshold">
            <ThresholdSlider
                v-model="threshold"
                @update:model-value="updateThreshold"
              />
            </SidebarPanel>
        <SidebarPanel title="Performance">
          <PerformanceMetrics :metrics="metrics" />
        </SidebarPanel>
        <SidebarPanel title="Config">
          <ConfigInfo :config="processingConfig" />
        </SidebarPanel>
        <AppVersion />
      </template>

      <template #content>
        <ZoneEditor
          :stream-url="videoFeedUrl"
          :zones="zones"
          :mode="currentMode"
          :editing-zone-id="editingZoneId"
          :selected-zone="selectedZone"
          :af-window="afWindow"
          @zone-created="handleZoneCreated"
          @zone-updated="handleZoneUpdated"
          @zone-deleted="handleZoneDeleted"
          @zone-selected="handleZoneSelect"
          @af-window-created="handleAFWindowCreated"
        />

        <div class="mt-4">
          <EventList
            :events="events"
            :connected="eventsConnected"
            :error="eventsError"
          />
        </div>
      </template>
    </SidebarLayout>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useZones } from '../composables/useZones'
import { useMetrics } from '../composables/useMetrics'
import { useEvents } from '../composables/useEvents'
import { streamAPI } from '../utils/api'
import Message from 'primevue/message'
import Card from 'primevue/card'
import SidebarLayout from '../components/layout/SidebarLayout.vue'
import SidebarPanel from '../components/layout/SidebarPanel.vue'
import ZoneEditor from '../components/stream/ZoneEditor.vue'
import Toolbar from '../components/stream/Toolbar.vue'
import ZoneList from '../components/stream/ZoneList.vue'
import PerformanceMetrics from '../components/stream/PerformanceMetrics.vue'
import CameraControls from '../components/stream/CameraControls.vue'
import ThresholdSlider from '../components/detector/ThresholdSlider.vue'
import EventList from '../components/stream/EventList.vue'
import AppVersion from '../components/stream/AppVersion.vue'
import ConfigInfo from '../components/stream/ConfigInfo.vue'
import SaveClipButton from '../components/stream/SaveClipButton.vue'

const {
  zones,
  selectedZone,
  loading,
  error,
  editingZoneId,
  fetchZones,
  createZone,
  updateZone,
  deleteZone,
  selectZone,
  startEditingZone,
  stopEditingZone,
  scheduleAutoSave
} = useZones()

const {
  metrics,
  startPolling,
  stopPolling
} = useMetrics()

const {
  events,
  connected: eventsConnected,
  error: eventsError,
  start: startEvents,
  stop: stopEvents
} = useEvents(50)

const currentMode = ref('view')
const threshold = ref(0.3)
const processingConfig = ref({})

const afWindow = ref(null)

const videoFeedUrl = computed(() => streamAPI.getVideoFeedUrl())

async function handleZoneCreated(zone) {
  const success = await createZone(zone)
  if (success) {
    currentMode.value = 'view'
    startEditingZone(zone.name)
  }
}

async function handleZoneUpdated(name, data) {
  await updateZone(name, data)
}

async function handleZoneDeleted(name) {
  await deleteZone(name)
}

function handleZoneDelete(name) {
  if (confirm(`Are you sure you want to delete zone "${name}"?`)) {
    deleteZone(name)
  }
}

function handleZoneSelect(zoneName) {
  if (editingZoneId.value && editingZoneId.value !== zoneName) {
    stopEditingZone()
  }
  startEditingZone(zoneName)
  currentMode.value = 'view'
}

function handleZoneUpdate(zone) {
  scheduleAutoSave(zone)
}

function handleStopEdit() {
  stopEditingZone()
}

function handleModeChange(mode) {
  currentMode.value = mode
  if (editingZoneId.value && (mode === 'line' || mode === 'polygon')) {
    stopEditingZone()
  }
}

async function updateThreshold(value) {
  threshold.value = value
  try {
    await streamAPI.updateThreshold(value)
  } catch (err) {
    console.error('Failed to save threshold:', err)
  }
}

function handleSetAFWindow() {
  currentMode.value = 'af_window'
  stopEditingZone()
}

async function handleResetAFWindow() {
  try {
    await streamAPI.resetCameraAutofocus()
    afWindow.value = null
  } catch (err) {
    console.error(err)
    afWindow.value = null
  }
}

async function handleAFWindowCreated(window) {
  try {
    // window is [x, y, w, h] normalized
    await streamAPI.updateCameraSettings({ af_window: window })
  } catch (err) {
    console.error(err)
  }
  // Always update local state to show the window
  afWindow.value = window
  currentMode.value = 'view'
}

async function checkCameraSupport() {
  try {
    const res = await streamAPI.getCameraSettings()
    if (res.data.af_window) {
      afWindow.value = res.data.af_window
    }
  } catch (err) {
    console.warn('Could not check camera settings:', err)
  }
}

async function loadThreshold() {
  try {
    const res = await streamAPI.getThreshold()
    if (res.data.threshold !== undefined) {
      threshold.value = res.data.threshold
    }
  } catch (err) {
    console.warn('Could not load threshold:', err)
  }
}

async function loadConfig() {
  try {
    const res = await streamAPI.getConfig()
    processingConfig.value = res.data
  } catch (err) {
    console.warn('Could not load config:', err)
  }
}

onMounted(async () => {
  await fetchZones()
  checkCameraSupport()
  loadThreshold()
  loadConfig()
  startPolling(500)
  startEvents()
})

onUnmounted(() => {
  stopPolling()
  stopEvents()
})
</script>

<style scoped>
/* No custom CSS needed - using Tailwind utilities */
</style>
