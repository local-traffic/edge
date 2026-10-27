<template>
  <Panel header="App Version" toggleable :collapsed="collapsed">
    <div>
    <p>Version: <code>{{ version }}</code></p>
    <p>Built: {{ rawDate }}</p>
    </div>
  </Panel>
</template>

<script setup>
    import { computed } from 'vue'

// The variables are automatically available globally
const version = __APP_VERSION__
const rawDate = __APP_DATE__
</script>

<style scoped>
/* No custom CSS needed - using Tailwind utilities */
</style>
