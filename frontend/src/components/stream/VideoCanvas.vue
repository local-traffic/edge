<template>
  <div class="w-full relative">
    <div ref="containerRef" class="relative w-full bg-[var(--bg-primary)] rounded-lg overflow-hidden">
      <!-- MJPEG Stream -->
      <img
        ref="videoRef"
        :src="streamUrl"
        alt="Live video stream"
        class="block w-full h-auto"
        @load="handleVideoLoad"
        @error="handleVideoError"
      />

      <!-- Canvas Overlay for Zones -->
      <canvas
        ref="canvasRef"
        class="absolute top-0 left-0 w-full h-full z-10 cursor-crosshair pointer-events-auto"
        :width="canvasWidth"
        :height="canvasHeight"
        @click="handleClick"
        @mousemove="handleMouseMove"
        @mousedown="handleMouseDown"
        @mouseup="handleMouseUp"
        @mouseleave="handleMouseLeave"
      ></canvas>
    </div>

    <div v-if="error" class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-[var(--danger)] text-white px-8 py-4 rounded font-semibold">
      {{ error }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import {
  drawLine,
  drawPolygon,
  drawHandle,
  clearCanvas
} from '../../utils/canvas'

const props = defineProps({
  streamUrl: {
    type: String,
    required: true
  },
  zones: {
    type: Array,
    default: () => []
  },
  editMode: {
    type: String,
    default: 'view',
    validator: (value) => ['view', 'line', 'polygon', 'edit', 'af_window'].includes(value)
  },
  drawingPoints: {
    type: Array,
    default: () => []
  },
  selectedHandle: {
    type: Number,
    default: -1
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

const emit = defineEmits([
  'canvas-click',
  'canvas-mouse-move',
  'canvas-mouse-down',
  'canvas-mouse-up',
  'video-load',
  'video-error',
  'canvas-resize'
])

const containerRef = ref(null)
const videoRef = ref(null)
const canvasRef = ref(null)
const ctx = ref(null)
const canvasWidth = ref(0)
const canvasHeight = ref(0)
const error = ref(null)

let resizeObserver = null

// Canvas helper functions
function initCanvas(canvas) {
  ctx.value = canvas.getContext('2d')
}

// Convert normalized coordinates (0-1) to canvas pixel coordinates
// This is the ONLY place where conversion to pixels happens
function normalizedToCanvas(normalizedX, normalizedY) {
  return {
    x: normalizedX * canvasWidth.value,
    y: normalizedY * canvasHeight.value
  }
}

function canvasToNormalized(canvasX, canvasY) {
  return {
    x: canvasX /  canvasWidth.value,
    y: canvasY / canvasHeight.value
  }
}

function getMousePos(event) {
  if (!canvasRef.value) return { x: 0, y: 0 }

  const rect = canvasRef.value.getBoundingClientRect()
  return {
    x: event.clientX - rect.left,
    y: event.clientY - rect.top
  }
}

function clear() {
  if (!ctx.value) return
  clearCanvas(ctx.value, canvasWidth.value, canvasHeight.value)
}

function drawLineZoneLocal(points, options = {}) {
  if (!ctx.value || points.length < 2) return

  const canvasPoints = points.map(p => normalizedToCanvas(p.x, p.y))
  drawLine(
    ctx.value,
    canvasPoints,
    options.color || '#00d4ff',
    options.lineWidth || 3
  )
}

function drawPolygonZoneLocal(points, options = {}) {
  if (!ctx.value || points.length < 3) return

  const canvasPoints = points.map(p => normalizedToCanvas(p.x, p.y))
  drawPolygon(
    ctx.value,
    canvasPoints,
    options.strokeColor || '#00d4ff',
    options.fillColor || 'rgba(0, 212, 255, 0.1)',
    options.lineWidth || 3
  )
}

function drawHandlesLocal(points, selectedIndex = -1) {
  if (!ctx.value) return

  points.forEach((point, index) => {
    const canvasPoint = normalizedToCanvas(point.x, point.y)
    drawHandle(
      ctx.value,
      canvasPoint.x,
      canvasPoint.y,
      index === selectedIndex,
      6
    )
  })
}

function handleVideoLoad() {
  if (!videoRef.value) return

  // Update canvas size to match video
  //vo 
  //canvasWidth.value = videoRef.value.naturalWidth || videoRef.value.width
  //canvasHeight.value = videoRef.value.naturalHeight || videoRef.value.height

  canvasWidth.value =  videoRef.value.width
  canvasHeight.value =  videoRef.value.height

  nextTick(() => {
    console.log('VideoCanvas: emitting resize', canvasWidth.value, canvasHeight.value)
    if (canvasRef.value) {
      initCanvas(canvasRef.value)
      emit('canvas-resize', { width: canvasWidth.value, height: canvasHeight.value })
    }

    error.value = null
    emit('video-load')
    redrawZones()
  })
}

function handleVideoError(event) {
  error.value = 'Failed to load video stream'
  emit('video-error', event)
}

function handleClick(event) {
  const pos = getMousePos(event)
  const normalized = canvasToNormalized(pos.x, pos.y)
  emit('canvas-click', normalized)
}

function handleMouseMove(event) {
  const pos = getMousePos(event)
  const normalized = canvasToNormalized(pos.x, pos.y)
  emit('canvas-mouse-move', normalized, event)
}

function handleMouseDown(event) {
  const pos = getMousePos(event)
  const normalized = canvasToNormalized(pos.x, pos.y)
  emit('canvas-mouse-down', normalized, event)
}

function handleMouseUp(event) {
  const pos = getMousePos(event)
  const normalized = canvasToNormalized(pos.x, pos.y)
  emit('canvas-mouse-up', normalized, event)
}

function handleMouseLeave(event) {
  emit('canvas-mouse-up', null, event)
}

function redrawZones() {
  if (!canvasRef.value) return

  clear()

  // Draw existing zones
  // All zone coordinates are stored in normalized format (0-1)
  // Conversion to canvas pixels happens in drawLineZoneLocal/drawPolygonZoneLocal
  props.zones.forEach(zone => {
    const points = zone.geometry.map(g => ({ x: g[0], y: g[1] }))
    
    const isEditing = props.editingZoneId === zone.name
    const isSelected = props.selectedZone?.name === zone.name

    // Different colors for different states (using CSS variables)
    const rootStyles = getComputedStyle(document.documentElement)
    let color = rootStyles.getPropertyValue('--zone-normal').trim()
    let fillColor = 'rgba(0, 212, 255, 0.1)'
    let lineWidth = 3

    if (isEditing) {
      color = rootStyles.getPropertyValue('--zone-editing').trim()
      fillColor = 'rgba(255, 170, 68, 0.2)'
      lineWidth = 4
    } else if (isSelected) {
      color = rootStyles.getPropertyValue('--zone-selected').trim()
      fillColor = 'rgba(68, 255, 68, 0.1)'
      lineWidth = 3
    }

    if (zone.type === 'line') {
      drawLineZoneLocal(points, {
        color: color,
        lineWidth: lineWidth
      })
    } else if (zone.type === 'polygon') {
      drawPolygonZoneLocal(points, {
        strokeColor: color,
        fillColor: fillColor,
        lineWidth: lineWidth
      })
    }
  })

  // Draw current drawing points (if in drawing mode)
  if (props.drawingPoints.length > 0) {
    const points = props.drawingPoints
    const rootStyles = getComputedStyle(document.documentElement)
    const editingColor = rootStyles.getPropertyValue('--zone-editing').trim()

    if (props.editMode === 'line' && points.length >= 1) {
      drawLineZoneLocal(points, {
        color: editingColor,
        lineWidth: 2
      })
      drawHandlesLocal(points, props.selectedHandle)
    } else if (props.editMode === 'polygon' && points.length >= 2) {
      drawPolygonZoneLocal(points, {
        strokeColor: editingColor,
        fillColor: 'rgba(255, 170, 68, 0.1)',
        lineWidth: 2
      })
      drawHandlesLocal(points, props.selectedHandle)
    } else if (props.editMode === 'af_window' && points.length >= 2) {
      // Draw Red AF Window
      const p1 = points[0]
      const p2 = points[points.length - 1]
      const rectPoints = [
        { x: p1.x, y: p1.y },
        { x: p2.x, y: p1.y },
        { x: p2.x, y: p2.y },
        { x: p1.x, y: p2.y }
      ]
      drawPolygonZoneLocal(rectPoints, {
        strokeColor: '#ff3333',
        fillColor: 'rgba(255, 50, 50, 0.2)',
        lineWidth: 2
      })
    }
  }

  // Draw active AF Window (if defined)
  if (props.afWindow && props.afWindow.length === 4) {
    const [x, y, w, h] = props.afWindow
    const rectPoints = [
      { x: x, y: y },
      { x: x + w, y: y },
      { x: x + w, y: y + h },
      { x: x, y: y + h }
    ]
    drawPolygonZoneLocal(rectPoints, {
      strokeColor: '#ff3333',
      fillColor: 'rgba(255, 50, 50, 0.1)',
      lineWidth: 2
    })
  }

  // Draw handles when editing an existing zone
  if (props.editingZoneId && props.drawingPoints.length > 0) {
    drawHandlesLocal(props.drawingPoints, props.selectedHandle)
  }
}

// Watch for zone changes and redraw
watch(
  () => [props.zones, props.drawingPoints, props.selectedHandle, props.editingZoneId, props.selectedZone, props.afWindow],
  redrawZones,
  { deep: true }
)

onMounted(() => {
  // Set up resize observer to handle container size changes
  if (containerRef.value) {
    resizeObserver = new ResizeObserver(() => {
      if (videoRef.value) {
        handleVideoLoad()
      }
    })
    resizeObserver.observe(containerRef.value)
  }

  // Initialize canvas if video is already loaded
  if (videoRef.value && videoRef.value.complete) {
    handleVideoLoad()
  }
})

onUnmounted(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
  }
})
</script>

<style scoped>
/* No custom CSS needed - using Tailwind utilities */
</style>
