<template>
  <div class="card flex flex-col">
    <div class="flex justify-between items-center mb-4">
      <h2 class="text-2xl font-bold">Traffic Statistics</h2>
      <div class="flex gap-4 items-center">
        <div class="flex gap-3">
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" v-model="mergeDirections" @change="fetchStats"
                   class="w-4 h-4 cursor-pointer" />
            <span class="text-sm">Merge Directions</span>
          </label>
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" v-model="groupVehicles" @change="fetchStats"
                   class="w-4 h-4 cursor-pointer" />
            <span class="text-sm">Group as Vehicles</span>
          </label>
        </div>
        <label>Time Range:</label>
        <select v-model="duration" @change="fetchStats" class="p-2 rounded bg-surface-ground border border-surface-border text-white bg-gray-800 border-gray-700">
          <option :value="4">Last 4 Hours (10 min intervals)</option>
          <option :value="12">Last 12 Hours (30 min intervals)</option>
          <option :value="24">Last 24 Hours (1 hour intervals)</option>
          <option :value="168">Last 7 Days (6 hour intervals)</option>
        </select>
        <button @click="fetchStats" class="pi pi-refresh p-2 rounded hover:bg-surface-hover"></button>
      </div>
    </div>
    <div class="flex flex-col">
    <div class=" bg-surface-card rounded p-4 h-80 ">
      <h3 class="text-lg font-semibold mb-2">Traffic Over Time</h3>
      <Bar v-if="chartData && !loading" :data="chartData" :options="chartOptions" class="h-1/4" />
      <div v-else class="flex items-center justify-center  text-gray-500">
        {{ loading ? 'Loading stats...' : 'No data available' }}
      </div>
    </div>
    <div class="bg-surface-card rounded p-4 h-80 mt-20">
      <h3 class="text-lg font-semibold mb-2">{{ histogramTitle }}</h3>
      <Bar v-if="speedChartData.datasets.length && !loading" :data="speedChartData" :options="histogramOptions" class="h-1/4" />
      <div v-else class="flex items-center justify-center text-gray-500">
        {{ loading ? 'Loading...' : 'No speed data available' }}
      </div>
    </div>
    <div class="bg-surface-card rounded p-4 h-80 mt-20">
      <h3 class="text-lg font-semibold mb-2">{{ noiseHistogramTitle }}</h3>
      <Bar v-if="noiseChartData.datasets.length && !loading" :data="noiseChartData" :options="noiseHistogramOptions" class="h-1/4" />
      <div v-else class="flex items-center justify-center text-gray-500">
        {{ loading ? 'Loading...' : 'No noise data available' }}
      </div>
    </div>
  </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from 'chart.js'
import { streamAPI } from '../utils/api'

ChartJS.register(Title, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

const duration = ref(4)
const stats = ref([])
const speedHistogram = ref([])
const noiseHistogram = ref([])
const loading = ref(false)
const mergeDirections = ref(true)
const groupVehicles = ref(true)

const chartOptions = {
  responsive: true ,
  maintainAspectRatio: false,
  scales: {
    x: { stacked: true },
    y: { stacked: true }
  },
  plugins: {
    legend: { position: 'top' },
    tooltip: {
      mode: 'index',
      intersect: false
    }
  }
}

const bucketSize = computed(() => {
  if (duration.value <= 4) return 5    // 5 min intervals (48 bars)
  if (duration.value <= 12) return 15  // 15 min intervals (48 bars)
  if (duration.value <= 24) return 30  // 30 min intervals (48 bars)
  return 240 // 4 hours (42 bars)
})

const chartData = computed(() => {
  const currentStats = stats.value || []
  
  // Sort stats by time bucket
  const sortedStats = [...currentStats].sort((a, b) => a.bucket_ts - b.bucket_ts)

  // Identify unique keys
  const stackKeys = [...new Set(sortedStats.map(s => {
    // When directions are merged, backend returns empty direction string
    if (s.direction === '' || !s.direction) {
      return `${s.zone_name} - ${s.class_name}`
    } else {
      return `${s.zone_name} (${s.direction}) - ${s.class_name}`
    }
  }))]

  // Generate complete time buckets based on duration
  const now = Math.floor(Date.now() / 1000)
  const bSize = bucketSize.value * 60 // seconds
  const endTs = Math.floor(now / bSize) * bSize
  const startTs = endTs - (duration.value * 3600)
  
  const uniqueBuckets = []
  for (let ts = startTs; ts <= endTs; ts += bSize) {
      uniqueBuckets.push(ts)
  }
  
  // Create labels
  const labels = uniqueBuckets.map(ts => {
      const d = new Date(ts * 1000)
      if (bucketSize.value >= 60) {
          return d.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
      }
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  })
  
  // Create datasets
  const datasets = stackKeys.map((key, index) => {
      const hue = (index * 137.5) % 360
      return {
          label: key,
          backgroundColor: `hsla(${hue}, 70%, 60%, 0.8)`,
          data: uniqueBuckets.map(ts => {
              const record = sortedStats.find(s => {
                const sKey = (s.direction === '' || !s.direction)
                  ? `${s.zone_name} - ${s.class_name}`
                  : `${s.zone_name} (${s.direction}) - ${s.class_name}`
                return s.bucket_ts === ts && sKey === key
              })
              return record ? record.count : 0
          })
      }
  })

  return { labels, datasets }
})

const histogramTitle = computed(() => {
  const now = new Date()
  const start = new Date(now.getTime() - duration.value * 3600 * 1000)
  const fmt = (d) => d.toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  })
  return `Speed Histogram: ${fmt(start)} to ${fmt(now)}`
})

const histogramOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    x: {
      stacked: true,
      title: { display: true, text: 'Speed (km/h)' }
    },
    y: {
      stacked: true,
      title: { display: true, text: 'Count' }
    }
  },
  plugins: {
    legend: { position: 'top' },
    tooltip: {
      mode: 'index',
      intersect: false
    }
  }
}

const speedChartData = computed(() => {
  const histogram = speedHistogram.value || []
  if (!histogram.length) return { labels: [], datasets: [] }

  // Build stack keys (same pattern as traffic chart)
  const stackKeys = [...new Set(histogram.map(s => {
    if (s.direction === '' || !s.direction) {
      return `${s.zone_name} - ${s.class_name}`
    } else {
      return `${s.zone_name} (${s.direction}) - ${s.class_name}`
    }
  }))]

  // Get unique speed bins and sort them
  const speedBins = [...new Set(histogram.map(s => s.speed_bin))].sort((a, b) => a - b)

  // Create labels (e.g., "0-5", "5-10", etc.)
  const binSize = 5
  const labels = speedBins.map(bin => `${bin}-${bin + binSize}`)

  // Create datasets (same color scheme as traffic chart)
  const datasets = stackKeys.map((key, index) => {
    const hue = (index * 137.5) % 360
    return {
      label: key,
      backgroundColor: `hsla(${hue}, 70%, 60%, 0.8)`,
      data: speedBins.map(bin => {
        const record = histogram.find(s => {
          const sKey = (s.direction === '' || !s.direction)
            ? `${s.zone_name} - ${s.class_name}`
            : `${s.zone_name} (${s.direction}) - ${s.class_name}`
          return s.speed_bin === bin && sKey === key
        })
        return record ? record.count : 0
      })
    }
  })

  return { labels, datasets }
})

const noiseHistogramTitle = computed(() => {
  const now = new Date()
  const start = new Date(now.getTime() - duration.value * 3600 * 1000)
  const fmt = (d) => d.toLocaleString('en-US', {
    month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
  })
  return `Noise Level Histogram: ${fmt(start)} to ${fmt(now)}`
})

const noiseHistogramOptions = {
  responsive: true,
  maintainAspectRatio: false,
  scales: {
    x: {
      stacked: true,
      title: { display: true, text: 'Noise Level dB(A)' }
    },
    y: {
      stacked: true,
      title: { display: true, text: 'Count' }
    }
  },
  plugins: {
    legend: { position: 'top' },
    tooltip: {
      mode: 'index',
      intersect: false
    }
  }
}

const noiseChartData = computed(() => {
  const histogram = noiseHistogram.value || []
  if (!histogram.length) return { labels: [], datasets: [] }

  const stackKeys = [...new Set(histogram.map(s => {
    if (s.direction === '' || !s.direction) {
      return `${s.zone_name} - ${s.class_name}`
    } else {
      return `${s.zone_name} (${s.direction}) - ${s.class_name}`
    }
  }))]

  const noiseBins = [...new Set(histogram.map(s => s.noise_bin))].sort((a, b) => a - b)

  const binSize = 5
  const labels = noiseBins.map(bin => `${bin}-${bin + binSize}`)

  const datasets = stackKeys.map((key, index) => {
    const hue = (index * 137.5) % 360
    return {
      label: key,
      backgroundColor: `hsla(${hue}, 70%, 60%, 0.8)`,
      data: noiseBins.map(bin => {
        const record = histogram.find(s => {
          const sKey = (s.direction === '' || !s.direction)
            ? `${s.zone_name} - ${s.class_name}`
            : `${s.zone_name} (${s.direction}) - ${s.class_name}`
          return s.noise_bin === bin && sKey === key
        })
        return record ? record.count : 0
      })
    }
  })

  return { labels, datasets }
})

async function fetchStats() {
  loading.value = true
  try {
    const [statsRes, histRes, noiseRes] = await Promise.all([
      streamAPI.getStats(duration.value, bucketSize.value, mergeDirections.value, groupVehicles.value),
      streamAPI.getSpeedHistogram(duration.value, 5, mergeDirections.value, groupVehicles.value),
      streamAPI.getNoiseHistogram(duration.value, 5, mergeDirections.value, groupVehicles.value)
    ])
    stats.value = statsRes.data.stats || []
    speedHistogram.value = histRes.data.histogram || []
    noiseHistogram.value = noiseRes.data.histogram || []
  } catch (e) {
    console.error("Failed to fetch stats:", e)
    stats.value = []
    speedHistogram.value = []
    noiseHistogram.value = []
  } finally {
    loading.value = false
  }
}

onMounted(fetchStats)
</script>

<style scoped>
</style>
