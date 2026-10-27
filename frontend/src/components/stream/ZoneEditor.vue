<template>
  <div class="relative w-full">
    <VideoCanvas
      :stream-url="streamUrl"
      :zones="zones"
      :edit-mode="mode"
      :drawing-points="drawingPoints"
      :selected-handle="selectedHandleIndex"
      :editing-zone-id="editingZoneId"
      :selected-zone="selectedZone"
      :af-window="afWindow"
      @canvas-click="handleCanvasClick"
      @canvas-mouse-move="handleCanvasMouseMove"
      @canvas-mouse-down="handleCanvasMouseDown"
      @canvas-mouse-up="handleCanvasMouseUp"
      @canvas-resize="handleCanvasResize"
    />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { nearestHandle, pointInPolygon, distanceToSegment } from '../../utils/canvas'
import VideoCanvas from './VideoCanvas.vue'

const props = defineProps({
  streamUrl: {
    type: String,
    required: true
  },
  zones: {
    type: Array,
    default: () => []
  },
  mode: {
    type: String,
    default: 'view',
    validator: (value) => ['view', 'line', 'polygon', 'edit', 'af_window'].includes(value)
  },
  editingZoneId: {
    type: String,
    default: null
  },
  selectedZone: {
    type: Object,
    default: null
  },
  afWindow: {
    type: Array,
    default: null
  }
})

const emit = defineEmits(['zone-created', 'zone-updated', 'zone-deleted', 'zone-selected', 'af-window-created'])

const drawingPoints = ref([])
const selectedHandleIndex = ref(-1)
const draggingHandle = ref(false)
const hasDragged = ref(false)
const isDrawingAF = ref(false)

const canvasWidth = ref(0)
const canvasHeight = ref(0)

function handleCanvasResize({ width, height }) {
  canvasWidth.value = width
  canvasHeight.value = height
}

function handleCanvasClick(normalized) {
  if (hasDragged.value) return

  if (props.mode === 'line') {
    handleLineDrawing(normalized)
  } else if (props.mode === 'polygon') {
    handlePolygonDrawing(normalized)
  } else {
    // Check if clicked on a zone
    // Iterate in reverse to match drawing order (top zone first)
    for (let i = props.zones.length - 1; i >= 0; i--) {
      const zone = props.zones[i]
      if (isPointInZone(normalized, zone)) {
        emit('zone-selected', zone.name)
        return
      }
    }
  }
}

function isPointInZone(point, zone) {
  // Zones are stored in normalized coordinates (0-1)
  const points = zone.geometry.map(g => ({ x: g[0], y: g[1] }))

  if (zone.type === 'polygon') {
    return pointInPolygon(point, points)
  } else if (zone.type === 'line') {
    for (let i = 0; i < points.length - 1; i++) {
      const dist = distanceToSegment(point, points[i], points[i + 1])
      if (dist < 0.02) return true
    }
  }
  return false
}

function handleLineDrawing(point) {
  if (drawingPoints.value.length === 0) {
    drawingPoints.value.push(point)
  } else if (drawingPoints.value.length === 1) {
    drawingPoints.value.push(point)
    finishZoneCreation('line')
  }
}

function handlePolygonDrawing(point) {
  const points = drawingPoints.value

  if (points.length >= 3) {
    const firstPoint = points[0]
    const distance = Math.sqrt(
      Math.pow(point.x - firstPoint.x, 2) + Math.pow(point.y - firstPoint.y, 2)
    )

    if (distance < 0.02) {
      finishZoneCreation('polygon')
      return
    }
  }

  drawingPoints.value.push(point)
}

function finishZoneCreation(type) {
  // Generate random name (e.g. Zone_123)
  const zoneName = `Zone_${Math.floor(Math.random() * 1000)}`
  
  // Keep coordinates normalized (0-1)
  const geometry = drawingPoints.value.map(p => [p.x, p.y])

  const zone = {
    name: zoneName,
    type: type,
    geometry
  }

  emit('zone-created', zone)
  drawingPoints.value = []
}

function handleCanvasMouseMove(normalized, event) {
  if (props.mode === 'af_window' && isDrawingAF.value) {
    // Update second point (end of rectangle)
    if (drawingPoints.value.length >= 1) {
      drawingPoints.value = [drawingPoints.value[0], normalized]
    }
    return
  }

  if (draggingHandle.value) {
    hasDragged.value = true
    if (selectedHandleIndex.value !== -1) {
      drawingPoints.value[selectedHandleIndex.value] = normalized
    }
  }
}

function handleCanvasMouseDown(normalized, event) {
  if (props.mode === 'af_window') {
    isDrawingAF.value = true
    drawingPoints.value = [normalized, normalized]
    return
  }

  hasDragged.value = false
  if (props.editingZoneId && drawingPoints.value.length > 0) {
    const handleIndex = nearestHandle(
      normalized,
      drawingPoints.value,
      0.05
    )

    if (handleIndex !== null && handleIndex !== -1) {
      selectedHandleIndex.value = handleIndex
      draggingHandle.value = true
    }
  }
}

function handleCanvasMouseUp(normalized, event) {
  if (props.mode === 'af_window' && isDrawingAF.value) {
    isDrawingAF.value = false
    
    // Calculate final rect from 2 points
    if (drawingPoints.value.length === 2) {
      const p1 = drawingPoints.value[0]
      const p2 = drawingPoints.value[1]
      
      const x = Math.min(p1.x, p2.x)
      const y = Math.min(p1.y, p2.y)
      const w = Math.abs(p2.x - p1.x)
      const h = Math.abs(p2.y - p1.y)
      
      // Emit if size is reasonable
      if (w > 0.01 && h > 0.01) {
        emit('af-window-created', [x, y, w, h])
      }
    }
    
    drawingPoints.value = []
    return
  }

  if (draggingHandle.value && props.editingZoneId && props.selectedZone) {
    // Keep coordinates normalized (0-1)
    const geometry = drawingPoints.value.map(p => [p.x, p.y])

    emit('zone-updated', props.editingZoneId, {
      ...props.selectedZone,
      geometry
    })
  }

  draggingHandle.value = false
  selectedHandleIndex.value = -1
}

watch(
  () => [props.editingZoneId, props.selectedZone, canvasWidth.value, canvasHeight.value],
  ([newId, newZone]) => {
    if (newId && newZone) {
      // Zones are stored in normalized coordinates (0-1)
      drawingPoints.value = newZone.geometry.map(g => ({
        x: g[0],
        y: g[1]
      }))
    } else {
      drawingPoints.value = []
      selectedHandleIndex.value = -1
      draggingHandle.value = false
    }
  },
  { immediate: true }
)

watch(() => props.mode, () => {
  drawingPoints.value = []
  selectedHandleIndex.value = -1
  draggingHandle.value = false
  isDrawingAF.value = false
})
</script>

<style scoped>
/* No custom CSS needed - using Tailwind utilities */
</style>
