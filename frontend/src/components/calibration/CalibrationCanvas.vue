<template>
  <div ref="containerRef" class="w-full relative">
    <!-- Canvas for grid (behind video, covers full area including padding) -->
    <canvas
      ref="canvasRef"
      class="absolute top-0 left-0 w-full h-full z-10 cursor-crosshair"
      :width="canvasWidth"
      :height="canvasHeight"
      @mousedown="handleMouseDown"
      @mousemove="handleMouseMove"
      @mouseup="handleMouseUp"
      @mouseleave="handleMouseUp"
    ></canvas>

    <!-- MJPEG Stream (centered with padding) -->
    <div class="flex justify-center py-[10%] px-[10%]">
      <img
        ref="videoRef"
        :src="streamUrl"
        alt="Live video stream"
        class="block max-w-full h-auto relative z-0"
        @load="handleVideoLoad"
        @error="handleVideoError"
      />
    </div>

    <!-- Error overlay -->
    <div
      v-if="error"
      class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-red-600 text-white px-6 py-3 rounded font-medium z-20"
    >
      {{ error }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue'
import {
  drawLine,
  drawHandle,
  clearCanvas,
  drawPerspectiveGrid,
  drawEdgeLabel,
  drawCornerLabel,
  lerp,
  EDGE_COLORS
} from '../../utils/canvas'

const props = defineProps({
  streamUrl: {
    type: String,
    required: true
  },
  corners: {
    type: Array,
    required: true
  },
  edgeLengths: {
    type: Object,
    required: true
  },
  selectedCorner: {
    type: Number,
    default: -1
  }
})

const emit = defineEmits(['corner-moved', 'corner-select'])

const containerRef = ref(null)
const videoRef = ref(null)
const canvasRef = ref(null)
const ctx = ref(null)
const canvasWidth = ref(0)
const canvasHeight = ref(0)
const error = ref(null)

// Video position within the canvas (to account for padding)
const videoOffset = ref({ x: 0, y: 0 })
const videoSize = ref({ width: 0, height: 0 })

const draggingCorner = ref(-1)
const localSelectedCorner = ref(-1)

let resizeObserver = null

const cornerLabels = ['TL', 'TR', 'BR', 'BL']
const cornerLabelOffsets = [
  { x: -15, y: -15 },  // TL - offset up-left
  { x: 15, y: -15 },   // TR - offset up-right
  { x: 15, y: 15 },    // BR - offset down-right
  { x: -15, y: 15 }    // BL - offset down-left
]

function initCanvas(canvas) {
  ctx.value = canvas.getContext('2d')
}

// Convert normalized coords (0-1 = video area) to canvas pixel coords
function normalizedToCanvas(normalizedX, normalizedY) {
  return {
    x: videoOffset.value.x + normalizedX * videoSize.value.width,
    y: videoOffset.value.y + normalizedY * videoSize.value.height
  }
}

// Convert canvas pixel coords to normalized coords (0-1 = video area)
function canvasToNormalized(canvasX, canvasY) {
  return {
    x: (canvasX - videoOffset.value.x) / videoSize.value.width,
    y: (canvasY - videoOffset.value.y) / videoSize.value.height
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

function findNearestCorner(normalized, threshold = 0.04) {
  for (let i = 0; i < 4; i++) {
    const corner = props.corners[i]
    const dist = Math.hypot(normalized.x - corner.x, normalized.y - corner.y)
    if (dist < threshold) {
      return i
    }
  }
  return -1
}

function handleVideoLoad() {
  if (!videoRef.value || !containerRef.value) return

  nextTick(() => {
    // Get container dimensions for canvas
    const containerRect = containerRef.value.getBoundingClientRect()
    canvasWidth.value = containerRect.width
    canvasHeight.value = containerRect.height

    // Get video position within container
    const videoRect = videoRef.value.getBoundingClientRect()
    videoOffset.value = {
      x: videoRect.left - containerRect.left,
      y: videoRect.top - containerRect.top
    }
    videoSize.value = {
      width: videoRect.width,
      height: videoRect.height
    }

    if (canvasRef.value) {
      initCanvas(canvasRef.value)
    }
    error.value = null
    redraw()
  })
}

function handleVideoError() {
  error.value = 'Failed to load video stream'
}

function handleMouseDown(event) {
  const pos = getMousePos(event)
  const normalized = canvasToNormalized(pos.x, pos.y)
  const cornerIndex = findNearestCorner(normalized)

  if (cornerIndex >= 0) {
    draggingCorner.value = cornerIndex
    localSelectedCorner.value = cornerIndex
    emit('corner-select', cornerIndex)
  }
}

function handleMouseMove(event) {
  if (draggingCorner.value >= 0) {
    const pos = getMousePos(event)
    const normalized = canvasToNormalized(pos.x, pos.y)
    emit('corner-moved', { index: draggingCorner.value, point: normalized })
  }
}

function handleMouseUp() {
  draggingCorner.value = -1
}

function redraw() {
  if (!ctx.value || canvasWidth.value === 0) return

  clearCanvas(ctx.value, canvasWidth.value, canvasHeight.value)

  // Convert corners to canvas coordinates
  const canvasCorners = props.corners.map(c => normalizedToCanvas(c.x, c.y))

  const gridSize = 5

  // Draw perspective grid with 2 cells extension beyond corners
  drawPerspectiveGrid(ctx.value, canvasCorners, gridSize, 'rgba(255, 255, 255, 0.4)', 1, 2)

  const lineWidth = 3

  // Draw each edge with its color
  // Top edge: TL -> TR (index 0 -> 1)
  drawLine(ctx.value, [canvasCorners[0], canvasCorners[1]], EDGE_COLORS.top, lineWidth)
  // Right edge: TR -> BR (index 1 -> 2) - no special color
  drawLine(ctx.value, [canvasCorners[1], canvasCorners[2]], '#888888', lineWidth)
  // Bottom edge: BR -> BL (index 2 -> 3)
  drawLine(ctx.value, [canvasCorners[2], canvasCorners[3]], EDGE_COLORS.bottom, lineWidth)
  // Left edge: BL -> TL (index 3 -> 0)
  drawLine(ctx.value, [canvasCorners[3], canvasCorners[0]], EDGE_COLORS.left, lineWidth)

  // Draw edge labels with matching colors
  drawEdgeLabel(ctx.value, canvasCorners[0], canvasCorners[1], `${props.edgeLengths.top}m`, -25, EDGE_COLORS.top)
  drawEdgeLabel(ctx.value, canvasCorners[3], canvasCorners[0], `${props.edgeLengths.left}m`, -25, EDGE_COLORS.left)
  drawEdgeLabel(ctx.value, canvasCorners[2], canvasCorners[3], `${props.edgeLengths.bottom}m`, 25, EDGE_COLORS.bottom)

  // Draw corner handles
  const selectedIdx = props.selectedCorner >= 0 ? props.selectedCorner : localSelectedCorner.value
  props.corners.forEach((corner, index) => {
    const pos = normalizedToCanvas(corner.x, corner.y)
    const isSelected = index === selectedIdx || index === draggingCorner.value
    drawHandle(ctx.value, pos.x, pos.y, isSelected, 10)
  })

  // Draw corner labels
  canvasCorners.forEach((pos, index) => {
    const offset = cornerLabelOffsets[index]
    drawCornerLabel(ctx.value, pos, cornerLabels[index], offset.x, offset.y)
  })

  // Calculate and display cell size in the center of the grid
  const cellWidth = ((props.edgeLengths.top + props.edgeLengths.bottom) / 2 / gridSize).toFixed(1)
  const cellHeight = (props.edgeLengths.left / gridSize).toFixed(1)
  const cellSizeLabel = `${cellWidth} x ${cellHeight} m`

  // Position label in center cell of the grid
  const centerU = 0.5
  const centerV = 0.5
  const topCenter = lerp(canvasCorners[0], canvasCorners[1], centerU)
  const bottomCenter = lerp(canvasCorners[3], canvasCorners[2], centerU)
  const center = lerp(topCenter, bottomCenter, centerV)

  drawEdgeLabel(ctx.value, { x: center.x, y: center.y - 15 }, { x: center.x, y: center.y + 15 }, cellSizeLabel, 0, '#ffffff')
}

// Watch for changes and redraw
watch(
  () => [props.corners, props.edgeLengths, props.selectedCorner],
  redraw,
  { deep: true }
)

onMounted(() => {
  if (containerRef.value) {
    resizeObserver = new ResizeObserver(() => {
      if (videoRef.value) {
        handleVideoLoad()
      }
    })
    resizeObserver.observe(containerRef.value)
  }

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
