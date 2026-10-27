<template>
  <div class="card">
    <Message v-if="error" severity="error" :closable="false">
      {{ error }}
    </Message>

    <SidebarLayout>
      <template #sidebar>
        <SidebarPanel title="Filters">
          <div class="flex flex-col gap-4">
            <div>
              <label class="block text-sm font-medium mb-2">Class</label>
              <Select
                v-model="classFilter"
                :options="classOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="All classes"
                class="w-full"
                showClear
              />
            </div>
            <div>
              <label class="block text-sm font-medium mb-2">Zone</label>
              <Select
                v-model="zoneFilter"
                :options="zoneOptions"
                optionLabel="label"
                optionValue="value"
                placeholder="All zones"
                class="w-full"
                showClear
              />
            </div>
            <Button
              label="Apply Filters"
              icon="pi pi-filter"
              @click="loadDetections"
              :loading="loading"
              class="w-full"
            />
          </div>
        </SidebarPanel>

        <SidebarPanel title="Statistics">
          <div class="text-sm space-y-2">
            <div class="flex justify-between">
              <span class="text-surface-500">Total:</span>
              <span class="font-medium">{{ total }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-surface-500">Showing:</span>
              <span class="font-medium">{{ detections.length }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-surface-500">Classes:</span>
              <span class="font-medium">{{ availableClasses.length }}</span>
            </div>
          </div>
        </SidebarPanel>

        <SidebarPanel v-if="selectedDetection" title="Selected Detection">
          <div class="text-sm space-y-2">
            <div class="flex justify-between">
              <span class="text-surface-500">Index:</span>
              <span>{{ selectedDetection.index }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-surface-500">Class:</span>
              <Tag :value="selectedDetection.class_name" severity="info" />
            </div>
            <div class="flex justify-between">
              <span class="text-surface-500">Day:</span>
              <span>{{ formatDetectionDay(selectedDetection) }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-surface-500">Time:</span>
              <span>{{ formatDetectionTime(selectedDetection) }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-surface-500">Event:</span>
              <span>{{ formatEventType(selectedDetection.event_type) }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-surface-500">Zone:</span>
              <span>{{ selectedDetection.zone_name }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-surface-500">ID:</span>
              <span>{{ selectedDetection.id }}</span>
            </div>
          </div>
        </SidebarPanel>

        <SidebarPanel title="Debug">
          <div class="flex flex-col gap-4">
            <div class="flex items-center gap-2">
              <Checkbox
                v-model="showDetections"
                inputId="show-detections"
                :binary="true"
              />
              <label for="show-detections" class="cursor-pointer">Show Detections</label>
            </div>
            <ThresholdSlider
              v-model="detectionThreshold"
              :disabled="!showDetections"
              :min="0.1"
              :max="1.0"
              :step="0.05"
            />
          </div>
        </SidebarPanel>
      </template>

      <template #content>
          <div v-if="loading" class="flex items-center justify-center h-64">
            <ProgressSpinner />
          </div>

        <div ref="thumbnailStripRef" class="relative">
        <div v-if="detections.length === 0" class=" justify-center h-64">
          <p>No detections found</p>
          <p class="text-sm">Try adjusting your filters or wait for new detections</p>
        </div>

         <div v-else class="flex gap-2">
            <div
              v-for="item in visibleThumbnails"
              :key="item.detection.id"
              class="w-20 cursor-pointer rounded-lg overflow-hidden border-2 transition-all hover:border-primary-500"
              :class="selectedDetection?.id === item.detection.id ? 'border-primary-500' : 'border-transparent'"
              @click="selectDetection(item.detection)"
            >
              <img
                :src="getThumbnailUrl(item.detection)"
                :alt="item.detection.class_name"
                class="w-full aspect-square object-cover"
                loading="lazy"
              />
              <div class="bg-black/70 px-1 py-0.5">
                <span class="text-xs text-white truncate block">
                 {{ item.detection.index }} - {{ item.detection.class_name }}
                </span>
                <span class="text-xs text-white truncate block">
                 {{ formatDetectionDay(item.detection) }}
                </span>
                <span class="text-xs text-white truncate block">
                 {{ formatDetectionTime(item.detection) }}
                </span>
              </div>
            </div>
            <div v-if="loadingMore" class="absolute inset-0 flex items-center justify-center">
              <ProgressSpinner style="width: 24px; height: 24px" />
            </div>
          </div>
        </div>

        <NavigationControls
          :current-index="currentIndex"
          :total-images="totalImages"
          :disabled="loading"
          @select="goToImage"
          class="max-w-full h-auto p-4"
        /> 

          <!-- Selected image viewer (below thumbnails) -->
          <div v-if="selectedDetection" class="border border-green-500 bg-gray-100">
              <Image :src="selectedImageUrl" alt="Image" imageClass="max-w-full h-auto" @error="handleImageError" />
          </div>

          <!-- Placeholder when nothing selected -->
          <div v-else class="flex-1 flex items-center justify-center text-surface-500">
            <p>Select a detection to view</p>
          </div>

      </template>
    </SidebarLayout>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { streamAPI } from '../utils/api'
import Message from 'primevue/message'
import Button from 'primevue/button'
import Select from 'primevue/select'
import Tag from 'primevue/tag'
import Image from 'primevue/image'
import Checkbox from 'primevue/checkbox'
import ProgressSpinner from 'primevue/progressspinner'
import SidebarLayout from '../components/layout/SidebarLayout.vue'
import SidebarPanel from '../components/layout/SidebarPanel.vue'
import NavigationControls from '../components/detector/NavigationControls.vue'
import ThresholdSlider from '../components/detector/ThresholdSlider.vue'

const detections = ref([])
const availableClasses = ref([])
const availableZones = ref([])
const classFilter = ref(null)
const zoneFilter = ref(null)
const selectedDetection = ref(null)
const loading = ref(false)
const loadingMore = ref(false)
const error = ref(null)
const total = ref(0)
const pageOffset = ref(0)
const limit = ref(48)
const currentIndex = ref(0)
const thumbnailStripStartIndex = ref(0)
const showDetections = ref(false)
const detectionThreshold = ref(0.3)
// match the w-20 / gap-2 tailwind classes of the thumbnail strip
const THUMBNAIL_WIDTH_REM = 5
const THUMBNAIL_GAP_REM = 0.5
const visibleThumbnailCount = ref(5)
const thumbnailStripRef = ref(null)
let thumbnailStripResizeObserver = null


const classOptions = computed(() => availableClasses.value.map(c => ({ label: c, value: c })))
const zoneOptions = computed(() => availableZones.value.map(z => ({ label: z, value: z })))
const selectedImageUrl = computed(() => {
  if (!selectedDetection.value || selectedDetection.value.index === undefined) return ''
  return streamAPI.getDetectionImageUrl(
    selectedDetection.value.index,
    showDetections.value,
    showDetections.value ? detectionThreshold.value : null
  )
})
const totalImages = computed(() => total.value)
const visibleThumbnails = computed(() => {
  const pageStart = thumbnailStripStartIndex.value - pageOffset.value
  if (pageStart < 0) return []
  return detections.value
    .slice(pageStart, pageStart + visibleThumbnailCount.value)
    .map((detection, i) => ({ offset: i, detection }))
})


async function loadDetections() {
  loading.value = true
  error.value = null
  pageOffset.value = 0
  currentIndex.value = 0
  thumbnailStripStartIndex.value = 0

  try {
    const params = {
      limit: limit.value,
      offset: 0
    }
    if (classFilter.value) params.class_name = classFilter.value
    if (zoneFilter.value) params.zone_name = zoneFilter.value

    const response = await streamAPI.getDetections(params)
    detections.value = response.data.detections || []
    total.value = response.data.total || 0
    availableClasses.value = response.data.classes || []
    availableZones.value = response.data.zones || []
    selectDetection(detections.value[0])
  } catch (err) {
    error.value = 'Failed to load detections'
    console.error('Error loading detections:', err)
  } finally {
    loading.value = false
  }
}

function selectDetection(detection) {
  selectedDetection.value = detection
}

async function goToImage(index) {
  if (index === currentIndex.value || loading.value) return
  if (index < 0 || index >= total.value) return

  currentIndex.value = index
  if (!isIndexInLoadedPage(index)) {
    await loadPageAround(index)
  }
  if (index !== currentIndex.value) return
  thumbnailStripStartIndex.value = index
  selectDetection(detections.value[index - pageOffset.value])
}

function isIndexInLoadedPage(index) {
  const lastNeededIndex = Math.min(index + visibleThumbnailCount.value, total.value) - 1
  return index >= pageOffset.value && lastNeededIndex < pageOffset.value + detections.value.length
}

async function loadPageAround(index) {
  loadingMore.value = true
  const pageStartIndex = Math.max(0, index - Math.floor(limit.value / 2))
  try {
    const params = { limit: limit.value, offset: pageStartIndex }
    if (classFilter.value) params.class_name = classFilter.value
    if (zoneFilter.value) params.zone_name = zoneFilter.value

    const response = await streamAPI.getDetections(params)
    if (index !== currentIndex.value) return
    detections.value = response.data.detections || []
    pageOffset.value = pageStartIndex
    thumbnailStripStartIndex.value = index
  } catch (err) {
    console.error('Error loading detections:', err)
  } finally {
    loadingMore.value = false
  }
}

function getThumbnailUrl(detection) {
  if (detection.index === undefined) return ''
  return streamAPI.getDetectionThumbnailUrl(detection.index)
}

function getImageUrl(detection) {
  if (!detection || detection.index === undefined) return ''
  return streamAPI.getDetectionImageUrl(
    detection.index,
    showDetections.value,
    showDetections.value ? detectionThreshold.value : null
  )
}

function formatEventType(type) {
  if (!type) return ''
  return type.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())
}

// dir is "YYYYMMDD-zone", id is "HHMMSS.micro" (see snapshot_saver.generate_filename_base)
function formatDetectionDay(detection) {
  const [, year, month, day] = detection.dir.match(/^(\d{4})(\d{2})(\d{2})/) || []
  return year ? `${year}-${month}-${day}` : ''
}

function formatDetectionTime(detection) {
  const [, hours, minutes, seconds] = detection.id.match(/^(\d{2})(\d{2})(\d{2})/) || []
  return hours ? `${hours}:${minutes}:${seconds}` : ''
}

function handleImageError(e) {
  console.error('Failed to load image')
}

function updateVisibleThumbnailCount() {
  const remPx = parseFloat(getComputedStyle(document.documentElement).fontSize)
  const stripWidthRem = thumbnailStripRef.value.clientWidth / remPx
  visibleThumbnailCount.value = Math.max(1, Math.floor((stripWidthRem + THUMBNAIL_GAP_REM) / (THUMBNAIL_WIDTH_REM + THUMBNAIL_GAP_REM)))
}

onMounted(() => {
  thumbnailStripResizeObserver = new ResizeObserver(updateVisibleThumbnailCount)
  thumbnailStripResizeObserver.observe(thumbnailStripRef.value)
  loadDetections()
})

onUnmounted(() => {
  thumbnailStripResizeObserver.disconnect()
})
</script>
