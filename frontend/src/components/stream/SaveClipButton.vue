<template>
  <Panel header="Save Clip">
    <div class="flex flex-col gap-3">
      <Button
        label="Save Clip"
        icon="pi pi-save"
        :loading="saving"
        @click="handleSave"
      />

      <Message v-if="message" :severity="messageType" :closable="true" @close="message = null">
        {{ message }}
      </Message>
    </div>
  </Panel>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { streamAPI } from '../../utils/api'
import Panel from 'primevue/panel'
import Button from 'primevue/button'
import Message from 'primevue/message'

const loading = ref(true)
const saving = ref(false)
const message = ref(null)
const messageType = ref('info')

let pollInterval = null


async function handleSave() {
  saving.value = true
  message.value = null

  try {
    const res = await streamAPI.saveClip()
    message.value = `Saved ${res.data.filename} (${res.data.duration}s)`
    messageType.value = 'success'
  } catch (err) {
    message.value = err.response?.data?.error || 'Failed to save clip'
    messageType.value = 'error'
  } finally {
    saving.value = false
  }
}

onMounted(() => {
})

onUnmounted(() => {
})
</script>
