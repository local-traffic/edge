<template>
  <div class="text-sm space-y-1">
    <div
      v-for="(value, key) in config"
      :key="key"
      class="flex justify-between gap-2 py-0.5"
    >
      <span class="text-[var(--text-color-secondary)] truncate">{{ formatKey(key) }}</span>
      <span class="font-mono text-right">{{ formatValue(value) }}</span>
    </div>
    <div v-if="!config || Object.keys(config).length === 0" class="text-[var(--text-color-secondary)]">
      No config loaded
    </div>
  </div>
</template>

<script setup>
defineProps({
  config: {
    type: Object,
    default: () => ({})
  }
})

function formatKey(key) {
  return key.replace(/_/g, ' ')
}

function formatValue(value) {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'number') return Number.isInteger(value) ? value : value.toFixed(2)
  return String(value)
}
</script>
