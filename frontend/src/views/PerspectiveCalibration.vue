<template>
  <div class="card">
    <Message v-if="error" severity="error" :closable="false" class="mb-4">
      {{ error }}
    </Message>

    <SidebarLayout>
      <template #sidebar>
        <SidebarPanel title="Edge Lengths">
          <DistanceInputs v-model="edgeLengths" @update:modelValue="scheduleAutoSave" />
        </SidebarPanel>

        <SidebarPanel title="Status">
          <div class="flex flex-col gap-3">
            <!-- Status indicator -->
            <div class="flex items-center gap-2 text-sm">
              <span
                :class="[
                  'w-2 h-2 rounded-full',
                  saving ? 'bg-yellow-500' : (hasCalibration ? 'bg-green-500' : 'bg-gray-400')
                ]"
              ></span>
              <span class="text-[var(--text-secondary)]">
                {{ saving ? 'Saving...' : (hasCalibration ? 'Perspective saved' : 'Not defined') }}
              </span>
            </div>

            <!-- Reset button -->
            <Button
              label="Reset to Default"
              icon="pi pi-refresh"
              severity="secondary"
              outlined
              @click="handleReset"
              class="w-full"
            />
          </div>
        </SidebarPanel>

        <SidebarPanel title="Instructions">
          <div class="text-sm text-[var(--text-secondary)] space-y-2">
            <p>
              <strong>1.</strong> Drag the 4 corner handles to match a known rectangle in your camera view (e.g., road markings, parking spots).
            </p>
            <p>
              <strong>2.</strong> Enter the real-world dimensions of the edges in meters.
            </p>
            <p class="text-xs opacity-70 mt-3">
              Changes are saved automatically. The 5x5 grid shows how the perspective transformation will distort the view.
            </p>
          </div>
        </SidebarPanel>
      </template>

      <template #content>
        <CalibrationCanvas
          :stream-url="videoFeedUrl"
          :corners="corners"
          :edge-lengths="edgeLengths"
          :selected-corner="selectedCorner"
          @corner-moved="handleCornerMoved"
          @corner-select="handleCornerSelect"
        />
      </template>
    </SidebarLayout>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { usePerspective } from '../composables/usePerspective'
import { streamAPI } from '../utils/api'
import Message from 'primevue/message'
import Button from 'primevue/button'
import SidebarLayout from '../components/layout/SidebarLayout.vue'
import SidebarPanel from '../components/layout/SidebarPanel.vue'
import CalibrationCanvas from '../components/calibration/CalibrationCanvas.vue'
import DistanceInputs from '../components/calibration/DistanceInputs.vue'

const {
  corners,
  edgeLengths,
  saving,
  error,
  hasCalibration,
  fetchPerspective,
  savePerspective,
  resetToDefault,
  updateCorner
} = usePerspective()

const selectedCorner = ref(-1)
let autoSaveTimer = null

const videoFeedUrl = computed(() => streamAPI.getVideoFeedUrl())

function scheduleAutoSave() {
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer)
  }
  autoSaveTimer = setTimeout(() => {
    savePerspective()
  }, 500)
}

function handleCornerMoved({ index, point }) {
  updateCorner(index, point)
  scheduleAutoSave()
}

function handleCornerSelect(index) {
  selectedCorner.value = index
}

function handleReset() {
  resetToDefault()
  selectedCorner.value = -1
  scheduleAutoSave()
}

onMounted(() => {
  fetchPerspective()
})

onUnmounted(() => {
  if (autoSaveTimer) {
    clearTimeout(autoSaveTimer)
  }
})
</script>
