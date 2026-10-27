<template>
  <div>
  <Slider v-model="sliderPosition"
          :min="0"
          :max="Math.max(totalImages - 1, 0)"
          :disabled="disabled"
          @change="onSliderChange"/>
  <div class="flex items-center justify-center gap-4 py-4">
    <Button
      label="Previous"
      icon="pi pi-arrow-left"
      :disabled="!hasPrev || disabled"
      severity="secondary"
      @click="$emit('select', currentIndex - 1)"
    />

    <div class="min-w-[100px] flex justify-center">
      <Chip :label="`${sliderPosition + 1} / ${totalImages}`" />
    </div>

    <Button
      label="Next"
      icon="pi pi-arrow-right"
      icon-pos="right"
      :disabled="!hasNext || disabled"
      severity="secondary"
      @click="$emit('select', currentIndex + 1)"
    />
  </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import Button from 'primevue/button'
import Chip from 'primevue/chip'
import Slider from 'primevue/slider'



const props = defineProps({
  currentIndex: {
    type: Number,
    required: true
  },
  totalImages: {
    type: Number,
    required: true
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['select'])

const SLIDER_SETTLE_MS = 200
const sliderPosition = ref(props.currentIndex)
let sliderSettleTimer = null

watch(() => props.currentIndex, (index) => { sliderPosition.value = index })

const hasPrev = computed(() => props.currentIndex > 0)
const hasNext = computed(() => props.currentIndex < props.totalImages - 1)

function handleKeydown(event) {
  if (props.disabled) return

  if (event.key === 'ArrowLeft' && hasPrev.value) {
    emit('prev')
  } else if (event.key === 'ArrowRight' && hasNext.value) {
    emit('next')
  }
}

// Slider emits change on every drag step; only jump once the handle stops moving
function onSliderChange(index) {
  clearTimeout(sliderSettleTimer)
  sliderSettleTimer = setTimeout(() => {
    if (!props.disabled && index !== props.currentIndex) {
      emit('select', index)
    }
  }, SLIDER_SETTLE_MS)
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
  clearTimeout(sliderSettleTimer)
})
</script>

<style scoped>
/* No custom CSS needed - using Tailwind utilities */
</style>
