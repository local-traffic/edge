import axios from 'axios'

// Create axios instance with default config
const api = axios.create({
  baseURL: '/',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

// Stream API (port 9090, proxied through Vite)
export const streamAPI = {
  // Get all zones
  getZones: () => api.get('/api/zones'),

  // Create new zone
  createZone: (zone) => api.post('/api/zones', zone),

  // Update existing zone
  updateZone: (name, data) => api.put(`/api/zones/${name}`, data),

  // Delete zone
  deleteZone: (name) => api.delete(`/api/zones/${name}`),

  // Get performance metrics
  getMetrics: () => api.get('/metrics'),

  // Get traffic stats
  getStats: (duration, bucket, mergeDirections = false, groupVehicles = false) =>
    api.get('/api/stats', {
      params: {
        duration,
        bucket,
        merge_directions: mergeDirections,
        group_vehicles: groupVehicles
      }
    }),

  // Get speed histogram
  getSpeedHistogram: (duration, binSize = 5, mergeDirections = false, groupVehicles = false) =>
    api.get('/api/stats/speeds', {
      params: {
        duration,
        bin_size: binSize,
        merge_directions: mergeDirections,
        group_vehicles: groupVehicles
      }
    }),

  // Get noise level histogram
  getNoiseHistogram: (duration, binSize = 5, mergeDirections = false, groupVehicles = false) =>
    api.get('/api/stats/noise', {
      params: {
        duration,
        bin_size: binSize,
        merge_directions: mergeDirections,
        group_vehicles: groupVehicles
      }
    }),

  // Get track history
  getTracks: (minDistance = 0, maxHistory = 10) => api.get('/api/tracks', { params: { min_distance: minDistance, max_history: maxHistory } }),
  
  // Update track settings
  updateTrackSettings: (settings) => api.post('/api/tracks/settings', settings),

  // Camera settings
  getCameraSettings: () => api.get('/api/camera/settings'),
  updateCameraSettings: (settings) => api.post('/api/camera/settings', settings),
  resetCameraAutofocus: () => api.post('/api/camera/reset'),

  // Perspective calibration
  getPerspective: () => api.get('/api/perspective'),
  savePerspective: (data) => api.post('/api/perspective', data),
  deletePerspective: () => api.delete('/api/perspective'),

  // Detection threshold
  getThreshold: () => api.get('/api/threshold'),
  updateThreshold: (threshold) => api.post('/api/threshold', { threshold }),

  // Processing config (all settings)
  getConfig: () => api.get('/api/config'),

  // Video feed URL (MJPEG stream)
  getVideoFeedUrl: () => '/video_feed',

  // Clip save API
  saveClip: () => api.post('/api/clip/save'),

  // Events API
  getEvents: (limit = 50) => api.get('/api/events', { params: { limit } }),
  getEventsStreamUrl: () => '/api/events/stream',

  // Detection Snapshots API
  getDetections: (params = {}) => api.get('/api/detections', { params }),
  getDetectionImageUrl: (index, annotate = false, threshold = null) => {
    const params = new URLSearchParams({ annotate: annotate.toString() })
    if (threshold !== null) params.append('threshold', threshold.toString())
    params.append('_t', Date.now().toString())
    return `/api/image/${index}?${params.toString()}`
  },
  getDetectionThumbnailUrl: (index) => `/api/thumbnail/${index}`,
  getDetectionMetadata: (index) => api.get(`/api/detections/metadata/${index}`),
  updateDetectorSettings: (settings) => api.post('/api/settings', settings),

  // Noise measurement
  getNoiseDevices: () => api.get('/api/noise/devices'),
  getNoiseLevel: (n = 50) => api.get('/api/noise/level', { params: { n } }),
  setNoiseDevice: (deviceIndex) => api.post('/api/noise/device', { device_index: deviceIndex })
}

export default api
