<template>
  <Panel header="Auto Focus Editor">
    <p class="text-sm leading-relaxed mb-4">
      Set AutoFocus window for Pi Camera.
    </p>

    <div class="grid grid-cols-2 gap-3 mb-4">
      <Button
        label="Draw AF area"
        icon="pi pi-focus"
        :severity="active ? 'primary' : 'secondary'"
        :outlined="!active"
        @click="$emit('ret-afwindow')"
      />

      <Button
        label="Clear "
        icon="pi pi-refresh"
        severity="secondary"
        @click="$emit('reset-afwindow')"
      />
    </div>
  </Panel>
</template>

<script setup>
import Panel from 'primevue/panel'
import Button from 'primevue/button'

defineProps({
  active: {
    type: Boolean,
    default: false
  }
})

defineEmits(['ret-afwindow', 'reset-afwindow'])
</script>

<style scoped>
/* No custom CSS needed - using Tailwind utilities */
</style>
