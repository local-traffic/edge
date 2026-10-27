import { fileURLToPath, URL } from 'node:url';

import { defineConfig } from 'vite'
import { PrimeVueResolver } from '@primevue/auto-import-resolver';
import tailwindcss from '@tailwindcss/vite';
import vue from '@vitejs/plugin-vue';
import Components from 'unplugin-vue-components/vite';
import { execSync } from 'child_process'

// 1. Get Git Information
let commitHash = 'unknown'
let commitDate = 'unknown'

try {
  commitHash = execSync('git describe --tags --always --dirty').toString().trim()
  commitDate = execSync('git show -s --format=%cI HEAD').toString().trim()
} catch (e) {
  console.warn('Git info not available (not a git repo?)')
}

//const http_target = 'http://rpi:9090'
const http_target = 'http://localhost:9090'

// https://vite.dev/config/
export default defineConfig({
      optimizeDeps: {
        noDiscovery: true
    },
  plugins: [
        vue(),
        tailwindcss(),
        Components({
            resolvers: [PrimeVueResolver()]
        })
  ],
  resolve: {
        alias: {
            '@': fileURLToPath(new URL('./src', import.meta.url)),
 
        }
  },
  define: {
    __APP_VERSION__: JSON.stringify(commitHash),
    __APP_DATE__: JSON.stringify(commitDate)
  },
  server: {
    port: 3000,
    proxy: {
      // Proxy all API requests to Flask backend on port 9090
      '/api': {
        target: http_target,
        changeOrigin: true,
        secure: false,
        ws: true,
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('proxy error', err);
          });
          proxy.on('proxyReq', (proxyReq, req, _res) => {
            console.log('Sending Request to the Target:', req.method, req.url);
          });
          proxy.on('proxyRes', (proxyRes, req, _res) => {
            console.log('Received Response from the Target:', proxyRes.statusCode, req.url);
          });
        }
      },
      // Proxy video feed to Flask stream backend
      '/video_feed': {
        target: http_target,
        changeOrigin: true,
        secure: false,
        ws: false  // MJPEG doesn't need WebSocket
      },
      // Proxy metrics to Flask stream backend
      '/metrics': {
        target: http_target,
        changeOrigin: true,
        secure: false
      }
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: true
  },
  css: {
    preprocessorOptions: {
        scss: {
            api: 'modern-compiler'
        }
        }
    }
})
