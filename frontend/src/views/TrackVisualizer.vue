<template>
  <div class="card">
    <SidebarLayout>
      <template #sidebar>
        <SidebarPanel title="Tracks">
            <div class="flex gap-2 mb-2">
          <div class="mb-3">
            <span class="text-xs text-gray-400 block mb-1">Start-End Min Distance</span>
            <Dropdown 
                v-model="minDistance" 
                :options="minDistanceOptions" 
                optionLabel="label" 
                optionValue="value"
                class="w-full p-inputtext-sm" 
                @change="fetchTracks"
            />
          </div>

          <div class="mb-3">
            <span class="text-xs text-gray-400 block mb-1">History Limit</span>
            <Dropdown 
                v-model="historyLimit" 
                :options="historyOptions" 
                optionLabel="label" 
                optionValue="value"
                class="w-full p-inputtext-sm" 
                @change="updateHistoryLimit"
            />
          </div>
          </div>

          <div class="flex gap-2 mb-2">
            <Button size="small" label="Refresh" icon="pi pi-refresh" @click="fetchTracks" />
            <Button size="small" label="Show All" severity="secondary" @click="selectAll" />
            <Button size="small" label="Show None" severity="secondary" @click="deselectAll" />
          </div>
          <div v-if="loading && tracks.length === 0" class="p-4 text-center">Loading...</div>
          <div v-else class="flex flex-col gap-2 overflow-y-auto h-[calc(100vh-12rem)]">
             <Card 
                v-for="track in tracks" 
                :key="track.id"
                class="cursor-pointer hover:bg-[var(--surface-hover)] transition-colors border-l-4"
                :style="isSelected(track.id) ? getTrackStyle(track.id) : { borderLeftColor: 'transparent' }"
                @click="toggleSelection(track.id)"
             >
                <template #content>
                    <div class="flex justify-between items-center p-2">
                        <div class="flex flex-col">
                            <span class="font-bold text-sm">ID: {{ track.id }}</span>
                            <span class="text-xs text-gray-400">
                                {{ new Date(track.start_time * 1000).toLocaleTimeString() }}
                                ({{ track.points.length }} pts)
                            </span>
                        </div>
                        <div class="flex flex-col items-end">
                            <Tag :value="getClass(track.class_id)" severity="info" />
                            <span class="text-xs mt-1 text-gray-400">{{ (track.confidence * 100).toFixed(0) }}%</span>
                        </div>
                    </div>
                </template>
             </Card>
          </div>
        </SidebarPanel>
      </template>

      <template #content>
        <div ref="containerRef" class="relative w-full h-full bg-black flex items-center justify-center overflow-hidden">
            <!-- Background Stream -->
            <img 
                ref="imgRef"
                :src="streamUrl" 
                class="max-w-full max-h-full object-contain"
                @load="handleImageLoad" 
            />
            
            <!-- Canvas overlay -->
            <canvas 
                ref="canvasRef" 
                class="absolute top-0 left-0 pointer-events-none"
                :style="canvasStyle"
                :width="canvasWidth"
                :height="canvasHeight"
            ></canvas>
        </div>
      </template>
    </SidebarLayout>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import SidebarLayout from '../components/layout/SidebarLayout.vue'
import SidebarPanel from '../components/layout/SidebarPanel.vue'
import Button from 'primevue/button'
import Card from 'primevue/card'
import Tag from 'primevue/tag'
import Dropdown from 'primevue/dropdown'
import { streamAPI } from '../utils/api'

const tracks = ref([])
const selectedTrackIds = ref(new Set())
const loading = ref(false)
const containerRef = ref(null)
const imgRef = ref(null)
const canvasRef = ref(null)
const streamUrl = computed(() => streamAPI.getVideoFeedUrl())

const canvasWidth = ref(640) // Default
const canvasHeight = ref(480) // Default
const canvasStyle = ref({})

const minDistance = ref(30)
const minDistanceOptions = [
    { label: '30 px', value: 30 },
    { label: '50 px', value: 50 },
    { label: '100 px', value: 100 },
    { label: '300 px', value: 300 }
]

const historyLimit = ref(100)
const historyOptions = [
    { label: '10 Tracks', value: 10 },
    { label: '50 Tracks', value: 50 },
    { label: '100 Tracks', value: 100 },
    { label: '200 Tracks', value: 200 },
    { label: '500 Tracks', value: 500 },
    { label: '1000 Tracks', value: 1000 }
]

// Class map (could be fetched or hardcoded for now)
const classMap = {
    0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 
    5: 'bus', 7: 'truck'
}

function getClass(id) {
    return classMap[id] || `Class ${id}`
}

async function fetchTracks() {
    loading.value = true
    try {
        const response = await streamAPI.getTracks(minDistance.value,historyLimit.value)
        tracks.value = response.data.tracks
        if (response.data.history_length) {
            historyLimit.value = response.data.history_length
        }
    } catch (e) {
        console.error("Failed to fetch tracks", e)
    } finally {
        loading.value = false
    }
}

async function updateHistoryLimit() {
    try {
        await streamAPI.updateTrackSettings({ history_length: historyLimit.value })
        fetchTracks()
    } catch (e) {
        console.error("Failed to update history limit", e)
    }
}

function isSelected(id) {
    return selectedTrackIds.value.has(id)
}

function toggleSelection(id) {
    const newSet = new Set(selectedTrackIds.value)
    if (newSet.has(id)) {
        newSet.delete(id)
    } else {
        newSet.add(id)
    }
    selectedTrackIds.value = newSet
}

function selectAll() {
    selectedTrackIds.value = new Set(tracks.value.map(t => t.id))
}

function deselectAll() {
    selectedTrackIds.value = new Set()
}

function handleImageLoad() {
    updateCanvasSize()
}

function getTrackStyle(id) {
    const hue = (id * 137.508) % 360
    const color = `hsl(${hue}, 70%, 60%)`
    const bg = `hsla(${hue}, 70%, 60%, 0.15)`
    return {
        borderLeftColor: color,
        backgroundColor: bg
    }
}

function updateCanvasSize() {
    if (!imgRef.value || !canvasRef.value || !containerRef.value) return
    
    // Get displayed image dimensions
    const rect = imgRef.value.getBoundingClientRect()
    const containerRect = containerRef.value.getBoundingClientRect()
    
    // Set canvas dimensions to match actual image resolution (intrinsic)
    if (imgRef.value.naturalWidth) {
        canvasWidth.value = imgRef.value.naturalWidth
        canvasHeight.value = imgRef.value.naturalHeight
    }
    
    // Position canvas exactly over image
    canvasStyle.value = {
        width: `${rect.width}px`,
        height: `${rect.height}px`,
        top: `${rect.top - containerRect.top}px`,
        left: `${rect.left - containerRect.left}px`
    }
}

function drawTracks() {
    const canvas = canvasRef.value
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    
    const selected = tracks.value.filter(t => selectedTrackIds.value.has(t.id))
    
    selected.forEach(track => {
        if (!track.points || track.points.length < 2) return
        
        ctx.beginPath()
        ctx.strokeStyle = getColorForId(track.id)
        ctx.lineWidth = 4
        ctx.lineCap = 'round'
        ctx.lineJoin = 'round'
        
        ctx.moveTo(track.points[0].x, track.points[0].y)
        for (let i = 1; i < track.points.length; i++) {
            ctx.lineTo(track.points[i].x, track.points[i].y)
        }
        ctx.stroke()
        
        // Draw start/end points
        ctx.fillStyle = '#fff'
        ctx.beginPath()
        ctx.arc(track.points[0].x, track.points[0].y, 4, 0, Math.PI * 2)
        ctx.fill()
        
        const last = track.points[track.points.length-1]
        ctx.beginPath()
        ctx.arc(last.x, last.y, 4, 0, Math.PI * 2)
        ctx.fill()
    })
}

function getColorForId(id) {
    const hue = (id * 137.508) % 360
    return `hsl(${hue}, 70%, 60%)`
}

let resizeObserver = null
let interval = null

onMounted(() => {
    fetchTracks()
    
    //interval = setInterval(fetchTracks, 2000)
    
    if (containerRef.value) {
        resizeObserver = new ResizeObserver(() => {
            updateCanvasSize()
        })
        resizeObserver.observe(containerRef.value)
    }
})

onUnmounted(() => {
    if (interval) clearInterval(interval)
    if (resizeObserver) resizeObserver.disconnect()
})

watch(selectedTrackIds, () => {
    drawTracks()
})
</script>

<style scoped>
:deep(.p-card-body) {
    padding: 0;
}
:deep(.p-card-content) {
    padding: 0;
}
</style>
