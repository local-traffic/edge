<template>
  <div class="w-full">
    <Panel :header="title" toggleable :collapsed="defaultCollapsed">
      <slot />
    </Panel>
  </div>
</template>

<script setup>
import Panel from 'primevue/panel'

defineProps({
  title: {
    type: String,
    required: true
  },
  defaultCollapsed: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
/* No custom CSS needed - using Tailwind utilities */
</style>
