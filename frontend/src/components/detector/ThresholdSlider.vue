<template>
  <div class="flex flex-col gap-3" :class="{ 'opacity-50': disabled }">
    <label for="threshold-slider" class="font-semibold">Confidence Threshold: {{ formattedValue }}</label>
    <Slider
      id="threshold-slider"
      v-model="localValue"
      :min="min"
      :max="max"
      :step="step"
      :disabled="disabled"
      @change="handleChange"
    />
    <small class="text-[var(--text-color-secondary)] leading-snug">
      Adjust the confidence threshold to filter detections. Lower values show more detections, higher values show only high-confidence detections.
    </small>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import Slider from 'primevue/slider'

const props = defineProps({
  modelValue: {
    type: Number,
    required: true
  },
  min: {
    type: Number,
    default: 0.1
  },
  max: {
    type: Number,
    default: 1.0
  },
  step: {
    type: Number,
    default: 0.05
  },
  debounceMs: {
    type: Number,
    default: 300
  },
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const localValue = ref(props.modelValue)
let debounceTimer = null

const formattedValue = computed(() => `${(localValue.value * 100).toFixed(0)}%`)

watch(() => props.modelValue, (newValue) => {
  localValue.value = newValue
})

function handleChange() {
  if (debounceTimer) {
    clearTimeout(debounceTimer)
  }

  debounceTimer = setTimeout(() => {
    emit('update:modelValue', localValue.value)
  }, props.debounceMs)
}
</script>

<style scoped>
/* No custom CSS needed - using Tailwind utilities */
</style>
