<template>
  <div class="flex flex-col gap-4">
    <!-- Visual reference diagram -->
    <div class="flex justify-center mb-2">
      <svg width="120" height="100" viewBox="0 0 120 100">
        <!-- Quadrilateral edges with colors -->
        <line x1="20" y1="20" x2="100" y2="20" :stroke="colors.top" stroke-width="3" />
        <line x1="20" y1="20" x2="20" y2="80" :stroke="colors.left" stroke-width="3" />
        <line x1="20" y1="80" x2="100" y2="80" :stroke="colors.bottom" stroke-width="3" />
        <line x1="100" y1="20" x2="100" y2="80" stroke="#666" stroke-width="2" />
        <!-- Corner dots -->
        <circle cx="20" cy="20" r="4" fill="#fff" />
        <circle cx="100" cy="20" r="4" fill="#fff" />
        <circle cx="100" cy="80" r="4" fill="#fff" />
        <circle cx="20" cy="80" r="4" fill="#fff" />
        <!-- Edge labels -->
        <text x="60" y="12" text-anchor="middle" :fill="colors.top" font-size="11" font-weight="bold">Top</text>
        <text x="8" y="52" text-anchor="middle" :fill="colors.left" font-size="11" font-weight="bold" transform="rotate(-90, 8, 52)">Left</text>
        <text x="60" y="95" text-anchor="middle" :fill="colors.bottom" font-size="11" font-weight="bold">Bottom</text>
      </svg>
    </div>

    <!-- Top Edge -->
    <div class="flex flex-col gap-1">
      <label for="top-edge" class="text-sm font-medium flex items-center gap-2">
        <span class="w-3 h-3 rounded-sm" :style="{ backgroundColor: colors.top }"></span>
        Top Edge (meters)
      </label>
      <InputNumber
        id="top-edge"
        v-model="localValue.top"
        :min="0.1"
        :max="200"
        :minFractionDigits="1"
        :maxFractionDigits="2"
        :step="0.5"
        class="w-full"
        @update:modelValue="handleUpdate"
      />
    </div>

    <!-- Left Edge -->
    <div class="flex flex-col gap-1">
      <label for="left-edge" class="text-sm font-medium flex items-center gap-2">
        <span class="w-3 h-3 rounded-sm" :style="{ backgroundColor: colors.left }"></span>
        Left Edge (meters)
      </label>
      <InputNumber
        id="left-edge"
        v-model="localValue.left"
        :min="0.1"
        :max="200"
        :minFractionDigits="1"
        :maxFractionDigits="2"
        :step="0.5"
        class="w-full"
        @update:modelValue="handleUpdate"
      />
    </div>

    <!-- Bottom Edge -->
    <div class="flex flex-col gap-1">
      <label for="bottom-edge" class="text-sm font-medium flex items-center gap-2">
        <span class="w-3 h-3 rounded-sm" :style="{ backgroundColor: colors.bottom }"></span>
        Bottom Edge (meters)
      </label>
      <InputNumber
        id="bottom-edge"
        v-model="localValue.bottom"
        :min="0.1"
        :max="200"
        :minFractionDigits="1"
        :maxFractionDigits="2"
        :step="0.5"
        class="w-full"
        @update:modelValue="handleUpdate"
      />
    </div>
  </div>
</template>

<script setup>
import { reactive, watch } from 'vue'
import InputNumber from 'primevue/inputnumber'
import { EDGE_COLORS } from '../../utils/canvas'

const props = defineProps({
  modelValue: {
    type: Object,
    required: true
  }
})

const colors = EDGE_COLORS

const emit = defineEmits(['update:modelValue'])

const localValue = reactive({
  top: props.modelValue.top,
  left: props.modelValue.left,
  bottom: props.modelValue.bottom
})

// Watch for external changes to modelValue
watch(() => props.modelValue, (newVal) => {
  localValue.top = newVal.top
  localValue.left = newVal.left
  localValue.bottom = newVal.bottom
}, { deep: true })

function handleUpdate() {
  emit('update:modelValue', {
    top: localValue.top,
    left: localValue.left,
    bottom: localValue.bottom
  })
}
</script>
