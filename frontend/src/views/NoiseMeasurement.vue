<template>
  <div class="card flex flex-col">
    <h2 class="text-2xl font-bold mb-4">Noise Measurement</h2>

    <div class="bg-surface-card rounded p-4 mb-6">
      <h3 class="text-lg font-semibold mb-2">Audio Input Devices</h3>
      <DataTable :value="devices" :loading="devicesLoading" stripedRows size="small">
        <Column field="index" header="Index" style="width: 5rem" />
        <Column field="name" header="Name" />
        <Column field="channels" header="Channels" style="width: 7rem" />
        <Column field="sample_rate" header="Sample Rate" style="width: 8rem">
          <template #body="{ data }">{{ data.sample_rate }} Hz</template>
        </Column>
        <Column field="is_default" header="Default" style="width: 6rem">
          <template #body="{ data }">
            <Tag v-if="data.is_default" value="Default" severity="success" />
          </template>
        </Column>
        <Column header="" style="width: 6rem">
          <template #body="{ data }">
            <Button v-if="data.index !== activeDeviceIndex"
                    label="Use" size="small" severity="secondary"
                    @click="selectDevice(data.index)" />
            <Tag v-else value="Active" severity="info" />
          </template>
        </Column>
      </DataTable>
      <p v-if="activeDeviceName" class="mt-3 text-sm text-surface-500">
        Currently using: Device {{ activeDeviceIndex }} — {{ activeDeviceName }}
      </p>
    </div>

    <div class="bg-surface-card rounded p-4 h-80">
      <h3 class="text-lg font-semibold mb-2">Live Noise Level dB(A)</h3>
      <Line v-if="chartData.datasets.length" :data="chartData" :options="chartOptions" class="h-1/4" />
      <div v-else class="flex items-center justify-center text-gray-500">
        Waiting for readings...
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { Line } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, LineElement, PointElement, CategoryScale, LinearScale } from 'chart.js'
import DataTable from 'primevue/datatable'
import Column from 'primevue/column'
import Button from 'primevue/button'
import Tag from 'primevue/tag'
import { streamAPI } from '../utils/api'

ChartJS.register(Title, Tooltip, Legend, LineElement, PointElement, CategoryScale, LinearScale)

const devices = ref([])
const devicesLoading = ref(false)
const readings = ref([])
const activeDeviceIndex = ref(null)
let pollInterval = null

const activeDeviceName = computed(() => {
  if (activeDeviceIndex.value === null) return null
  const device = devices.value.find(d => d.index === activeDeviceIndex.value)
  return device ? device.name : `Device ${activeDeviceIndex.value}`
})

const chartData = computed(() => {
  if (!readings.value.length) return { labels: [], datasets: [] }
  return {
    labels: readings.value.map((_, i) => i),
    datasets: [{
      label: 'dB(A)',
      data: readings.value.map(r => r.db_a),
      borderColor: 'hsla(200, 70%, 60%, 1)',
      backgroundColor: 'hsla(200, 70%, 60%, 0.2)',
      fill: true,
      tension: 0.3,
      pointRadius: 0
    }]
  }
})

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 0 },
  scales: {
    x: { display: false },
    y: {
      title: { display: true, text: 'dB(A)' },
      suggestedMin: 20,
      suggestedMax: 80
    }
  },
  plugins: {
    legend: { display: false }
  }
}

async function fetchDevices() {
  devicesLoading.value = true
  try {
    const res = await streamAPI.getNoiseDevices()
    devices.value = res.data
  } catch (e) {
    console.error('Failed to fetch noise devices:', e)
  } finally {
    devicesLoading.value = false
  }
}

async function fetchLevel() {
  try {
    const res = await streamAPI.getNoiseLevel(100)
    readings.value = res.data.readings
    activeDeviceIndex.value = res.data.device_index
  } catch (e) {
    console.error('Failed to fetch noise level:', e)
  }
}

async function selectDevice(index) {
  try {
    await streamAPI.setNoiseDevice(index)
    activeDeviceIndex.value = index
  } catch (e) {
    console.error('Failed to set noise device:', e)
  }
}

onMounted(() => {
  fetchDevices()
  fetchLevel()
  pollInterval = setInterval(fetchLevel, 500)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<style scoped>
</style>
