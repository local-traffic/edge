<template>
  <Panel header="Performance Metrics">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="bg-[var(--surface-ground)] p-4 rounded-[var(--border-radius)] text-center">
        <div class="text-xs text-[var(--text-color-secondary)] uppercase tracking-wide mb-2">FPS</div>
        <div class="text-2xl font-bold tabular-nums">{{ formatNumber(metrics.fps, 1) }}</div>
      </div>

      <div class="bg-[var(--surface-ground)] p-4 rounded-[var(--border-radius)] text-center">
        <div class="text-xs text-[var(--text-color-secondary)] uppercase tracking-wide mb-2">Inference Time</div>
        <div class="text-2xl font-bold tabular-nums">{{ formatTime(metrics.inference_ms) }}</div>
      </div>

      <div class="bg-[var(--surface-ground)] p-4 rounded-[var(--border-radius)] text-center">
        <div class="text-xs text-[var(--text-color-secondary)] uppercase tracking-wide mb-2">Tracking Time</div>
        <div class="text-2xl font-bold tabular-nums">{{ formatTime(metrics.tracking_ms) }}</div>
      </div>
    </div>

  </Panel>
</template>

<script setup>
import Panel from 'primevue/panel'
import Chip from 'primevue/chip'
import Divider from 'primevue/divider'
import { DEFAULT_METRICS } from '../../composables/useMetrics'

defineProps({
  metrics: {
    type: Object,
    default: () => ({ ...DEFAULT_METRICS })
  }
})

function formatNumber(value, decimals = 0) {
  if (typeof value !== 'number') return '0'
  return value.toFixed(decimals)
}

function formatTime(value) {
  if (typeof value !== 'number') return '0 ms'
  return `${value.toFixed(1)} ms`
}

function formatTimestamp(timestamp) {
  if (!timestamp) return 'Never'
  const date = new Date(timestamp)
  return date.toLocaleTimeString()
}
</script>

<style scoped>
/* No custom CSS needed - using Tailwind utilities */
</style>
