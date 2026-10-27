import { createApp } from 'vue'
import { createPinia } from 'pinia'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import Material from '@primevue/themes/material'
import { definePreset } from '@primevue/themes'
import 'primeicons/primeicons.css'
//import './style.css'
import App from './App.vue'
import router from './router'

import '@/assets/tailwind.css';
import '@/assets/styles.scss';

const usePalette = (color) => Object.fromEntries(
   [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950].map(n => [n, `{${color}.${n}}`])
)


  const MyPreset = definePreset(Aura, {
    // // be prepared for customization but not needed now
    // components: {
    //   button: {
    //     colorScheme: {
    //       light: {
    //         root: {
    //           secondary: {
    //             background: '{slate.100}',
    //             hoverBackground: '{slate.200}',
    //             activeBackground: '{slate.300}',
    //             borderColor: '{slate.300}',
    //             hoverBorderColor: '{slate.400}',
    //             activeBorderColor: '{slate.500}',
    //             color: '{slate.700}',
    //             hoverColor: '{slate.800}',
    //             activeColor: '{slate.900}'
    //           }
    //         }
    //       },
    //       dark: {
    //         root: {
    //             secondary: {
    //               activeBackground: '{surface.200}',
    //               activeBorderColor: '{surface.600}',
    //               activeColor: '{surface.100}',
    //               background: '{surface.300}',
    //               borderColor: '{surface.800}',
    //               color: '{surface.300}'
    //             }
    //           },
    //           text: {
    //             secondary: {
    //                 activeBackground: '{surface.700}',
    //                 color: '{surface.900}',
    //                 hoverBackground: '{surface.300}',
    //               }
    //           }

    //         }
    //     }
    //   }
    // }
  })






const app = createApp(App)
const pinia = createPinia()

app.use(PrimeVue, {
  theme: {
    preset: MyPreset,
    options: {
      darkModeSelector: '.app-dark'
    }
  }
})
app.use(pinia)
app.use(router)
app.mount('#app')

// Make presets available globally for theme switching demo
window.__PRIMEVUE_PRESETS__ = { Aura, Material, MyPreset }
