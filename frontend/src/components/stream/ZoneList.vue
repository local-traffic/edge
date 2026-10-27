<template>
  <div>
    <Message v-if="zones.length === 0" severity="info">
      No zones defined. Click "New Line" or "New Polygon" to create zones.
    </Message>

    <div v-else class="flex flex-col gap-3">
      <Card
        v-for="(zone, index) in displayZones"
        :key="zone.id || index"
        class="transition-all duration-200 cursor-pointer hover:shadow-lg"
        :class="{
          'ring-2 ring-[var(--primary-color)]': isSelected(zone),
          'opacity-80 hover:opacity-100': !isSelected(zone)
        }"
        @click="handleZoneClick(zone)"
      >
        <template #content>
          <div class="flex items-center gap-3">
             <Tag :value="zone.type" :icon="zone.type === 'line' ? 'pi pi-minus' : 'pi pi-stop'" />
             
             <div class="flex-1 min-w-0">
                <InputText
                    v-if="isSelected(zone)"
                    v-model="zone.name"
                    class="w-full p-1 h-8 text-sm"
                    @click.stop
                    @blur="handleNameBlur(zone)"
                    @keyup.enter="handleNameEnter"
                />
                <div v-else class="font-semibold p-1 truncate">{{ zone.name }}</div>
             </div>

             <Button
                icon="pi pi-trash"
                text
                rounded
                severity="danger"
                @click.stop="handleDelete(zone)"
              />
          </div>
          
          <div v-if="isSelected(zone)" class="mt-3 flex items-center gap-2 pl-1">
            <Checkbox
              v-model="zone.store_picture"
              binary
              @change="handleCheckboxChange(zone)"
              @click.stop
            />
            <label class="text-sm cursor-pointer" @click.stop="zone.store_picture = !zone.store_picture; handleCheckboxChange(zone)">Store pictures</label>
          </div>
        </template>
      </Card>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import Card from 'primevue/card'
import Button from 'primevue/button'
import Message from 'primevue/message'
import Tag from 'primevue/tag'
import InputText from 'primevue/inputtext'
import Checkbox from 'primevue/checkbox'

const props = defineProps({
  zones: {
    type: Array,
    default: () => []
  },
  selectedZone: {
    type: Object,
    default: null
  },
  editingZoneId: {
    type: String,
    default: null
  }
})

const emit = defineEmits(['select', 'delete', 'update', 'stopEdit'])

// Display zones in reverse order (newest at top)
const displayZones = computed(() => [...props.zones].reverse())

function isSelected(zone) {
    return props.selectedZone?.name === zone.name
}

function handleZoneClick(zone) {
  emit('select', zone.name)
}

function handleNameChange(zoneName) {
  // emit('update', zoneName) - removed to prevent re-fetch loop
}

function handleCheckboxChange(zone) {
  emit('update', zone)
}

function handleNameBlur(zone) {
  emit('update', zone)
}

function handleNameEnter(event) {
  event.target.blur()
  emit('stopEdit')
}

function handleDelete(zone) {
  if (confirm(`Delete zone "${zone.name}"?`)) {
    emit('delete', zone.name)
  }
}
</script>

<style scoped>
:deep(.p-card-body) {
    padding: 1rem;
}
:deep(.p-card-content) {
    padding: 0;
}
</style>
