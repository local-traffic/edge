import { createRouter, createWebHistory } from 'vue-router'
import Detections from '../views/Detections.vue'
import LiveStream from '../views/LiveStream.vue'
import Statistics from '../views/Statistics.vue'
import TrackVisualizer from '../views/TrackVisualizer.vue'
import PerspectiveCalibration from '../views/PerspectiveCalibration.vue'
import StyleGuide from '../views/StyleGuide.vue'
import NoiseMeasurement from '../views/NoiseMeasurement.vue'

import AppLayout from '../components/layout/AppLayout.vue';

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      component: AppLayout,
    
      children: [
              {
        path: '/',
        name: '',
        component: LiveStream
      },
      {
        path: '/detections',
        name: 'detections',
        component: Detections
      },
      {
        path: '/stream',
        name: 'stream',
        component: LiveStream
      },
      {
        path: '/tracks',
        name: 'tracks',
        component: TrackVisualizer
      },
      {
        path: '/statistics',
        name: 'statistics',
        component: Statistics
      },
      {
        path: '/calibration',
        name: 'calibration',
        component: PerspectiveCalibration
      },
      {
        path: '/noise',
        name: 'noise',
        component: NoiseMeasurement
      },
      {
        path: '/style-guide',
        name: 'style-guide',
        component: StyleGuide
      }
      ]
    }
  ]
})

export default router
