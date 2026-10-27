<template>
  <Panel header="Zone Tools">
    <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
      <Button
        label="New Line"
        icon="pi pi-minus"
        :outlined="activeMode !== 'line'"
        @click="$emit('mode-change', 'line')"
      />

      <Button
        label="New Polygon"
        icon="pi pi-stop"
        :outlined="activeMode !== 'polygon'"
        @click="$emit('mode-change', 'polygon')"
      />
    </div>
  </Panel>
</template>

<script setup>
import Panel from 'primevue/panel'
import Button from 'primevue/button'

const props = defineProps({
  activeMode: {
    type: String,
    default: 'view',
    validator: (value) => ['view', 'line', 'polygon'].includes(value)
  }
})

defineEmits(['mode-change'])
</script>

<style scoped>
/* No custom CSS needed - using Tailwind utilities */
</style>
