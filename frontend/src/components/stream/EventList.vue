<template>
  <DataTable
    :value="events"
    scrollable
    size="small"
  >
    <template #header>
      <div class="flex justify-between items-center">
        <span class="font-semibold">Recent Events</span>
        <Tag v-if="connected" severity="success" value="Live" icon="pi pi-circle-fill" />
        <Tag v-else severity="secondary" value="Disconnected" icon="pi pi-circle" />
      </div>
    </template>

    <template #empty>
      <div class="text-center p-4 text-color-secondary">No events yet</div>
    </template>

    <Column field="time_str" header="Time" style="width: 80px">
      <template #body="{ data }">
        <span class="font-mono text-sm">{{ data.time_str }}</span>
      </template>
    </Column>

    <Column field="zone_name" header="Zone"  style="width: 140px" />

    <Column header="Event" style="width: 140px">
      <template #body="{ data }">
        <Tag :severity="eventSeverity(data.event_type)" :value="formatEvent(data)" />
      </template>
    </Column>

    <Column field="class_name" header="Class" style="width: 80px" />

    <Column header="Speed" style="width: 200px">
      <template #body="{ data }">
        <div v-if="data.speed?.is_valid" class="text-sm" :title="formatSpeedTooltip(data.speed)">
          <div class="font-semibold">{{ data.speed.avg_speed_kmh }} km/h</div>
          <div class="text-xs text-[var(--text-color-secondary)]">
            {{ data.speed.min_speed_kmh }}-{{ data.speed.max_speed_kmh }} km/h
            · {{ data.speed.distance_m }}m
            · {{ data.speed.duration_s }}s
          </div>
        </div>
        <span v-else class="text-color-secondary" :title="data.speed?.comment">-</span>
      </template>
      </Column>
    <Column header="Noise Level" style="width: 110px">
      <template #body="{ data }">
        <div v-if="data.noise?.db_a != null" class="text-sm">
          <span class="font-semibold">{{ data.noise.db_a }} dB(A)</span>
        </div>
        <span v-else class="text-color-secondary">-</span>
      </template>
    </Column>

      <Column header="Error est." style="width: 200px">
      <template #body="{ data }">
        <div v-if="data.speed?.is_valid" class="text-sm" :title="formatSpeedTooltip(data.speed)">
          <div class="font-semibold">{{ data.speed.speed_error_pct }}</div>
        </div>
        <span v-else class="text-color-secondary" :title="data.speed?.comment">-</span>
      </template>
    </Column>
  </DataTable>
</template>

<script setup>
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Tag from 'primevue/tag'

defineProps({
  events: {
    type: Array,
    default: () => []
  },
  connected: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: null
  }
})

function formatEvent(event) {
  const typeMap = {
    'line_cross': 'Cross',
    'zone_enter': 'Enter',
    'zone_exit': 'Exit'
  }
  const type = typeMap[event.event_type] || event.event_type
  return event.direction ? `${type} ${event.direction.toUpperCase()}` : type
}

function eventSeverity(eventType) {
  const severityMap = {
    'line_cross': 'info',
    'zone_enter': 'success',
    'zone_exit': 'warn'
  }
  return severityMap[eventType] || 'secondary'
}

function formatSpeedTooltip(speed) {
  return `Avg: ${speed.avg_speed_kmh} km/h
Max: ${speed.max_speed_kmh} km/h
Min: ${speed.min_speed_kmh} km/h
Distance: ${speed.distance_m} m
Duration: ${speed.duration_s} s
Error: ±${speed.error_pct}%`
}
</script>
