<template>
  <div class="card">
    <h1 class="text-3xl font-bold mb-2">Style Guide</h1>
    <p class="text-gray-400 mb-8">Design system for Traffic Detection UI</p>

    <!-- Colors Section -->
    <section class="mb-10">
      <h2 class="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">Colors</h2>

      <div class="mb-6 p-4 rounded-lg border border-gray-700" style="background-color: var(--p-surface-800)">
        <h3 class="text-sm font-medium text-gray-400 mb-3">Theme Switcher Demo</h3>
        <div class="flex gap-2">
          <Button label="Custom" :outlined="currentTheme !== 'MyPreset'" @click="setTheme('MyPreset')" size="small" />
          <Button label="Aura" :outlined="currentTheme !== 'Aura'" @click="setTheme('Aura')" size="small" />
          <Button label="Material" :outlined="currentTheme !== 'Material'" @click="setTheme('Material')" size="small" />
        </div>
      </div>

      <div class="mb-6">
        <h3 class="text-sm font-medium text-gray-400 mb-3">Primary Palette</h3>
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <ColorSwatch color="var(--p-primary-500)" name="Primary" cssVar="--p-primary-500" />
          <ColorSwatch color="var(--p-primary-600)" name="Primary Hover" cssVar="--p-primary-600" />
          <ColorSwatch color="var(--p-primary-700)" name="Primary Dark" cssVar="--p-primary-700" />
          <ColorSwatch color="var(--p-primary-300)" name="Primary Light" cssVar="--p-primary-300" />
          <ColorSwatch color="var(--p-indigo-500)" name="Accent" cssVar="--p-indigo-500" />
          <ColorSwatch color="var(--p-violet-500)" name="Accent Alt" cssVar="--p-violet-500" />
        </div>
      </div>

      <div class="mb-6">
        <h3 class="text-sm font-medium text-gray-400 mb-3">Surface Colors</h3>
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <ColorSwatch color="var(--p-surface-900)" name="Background" cssVar="--p-surface-900" />
          <ColorSwatch color="var(--p-surface-800)" name="Surface" cssVar="--p-surface-800" />
          <ColorSwatch color="var(--p-surface-700)" name="Surface Raised" cssVar="--p-surface-700" />
          <ColorSwatch color="var(--p-surface-500)" name="Border" cssVar="--p-surface-500" />
          <ColorSwatch color="var(--p-surface-400)" name="Text Muted" cssVar="--p-surface-400" />
          <ColorSwatch color="var(--p-surface-50)" name="Text" cssVar="--p-surface-50" />
        </div>
      </div>

      <div class="mb-6">
        <h3 class="text-sm font-medium text-gray-400 mb-3">Semantic Colors</h3>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <ColorSwatch color="var(--p-button-success-background)" name="Success" cssVar="--p-button-success-background" />
          <ColorSwatch color="var(--p-button-warn-background)" name="Warning" cssVar="--p-button-warn-background" />
          <ColorSwatch color="var(--p-button-danger-background)" name="Danger" cssVar="--p-button-danger-background" />
          <ColorSwatch color="var(--p-button-secondary-background)" name="Secondary" cssVar="--p-button-secondary-background" />
        </div>
      </div>

      <div class="mb-6">
        <h3 class="text-sm font-medium text-gray-400 mb-3">Chart Colors</h3>
        <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <ColorSwatch color="var(--p-teal-500)" name="Series 1" cssVar="--p-teal-500" />
          <ColorSwatch color="var(--p-indigo-500)" name="Series 2" cssVar="--p-indigo-500" />
          <ColorSwatch color="var(--p-amber-500)" name="Series 3" cssVar="--p-amber-500" />
          <ColorSwatch color="var(--p-pink-500)" name="Series 4" cssVar="--p-pink-500" />
          <ColorSwatch color="var(--p-violet-500)" name="Series 5" cssVar="--p-violet-500" />
          <ColorSwatch color="var(--p-cyan-500)" name="Series 6" cssVar="--p-cyan-500" />
        </div>
      </div>

      <div>
        <h3 class="text-sm font-medium text-gray-400 mb-3">Zone Colors (App-specific)</h3>
        <div class="grid grid-cols-3 gap-3">
          <ColorSwatch color="var(--zone-normal, #00d4ff)" name="Zone Normal" cssVar="--zone-normal" />
          <ColorSwatch color="var(--zone-editing, #ffaa44)" name="Zone Editing" cssVar="--zone-editing" />
          <ColorSwatch color="var(--zone-selected, #44ff44)" name="Zone Selected" cssVar="--zone-selected" />
        </div>
      </div>
    </section>

    <!-- Typography Section -->
    <section class="mb-10">
      <h2 class="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">Typography</h2>
      <div class="space-y-4">
        <div class="flex items-baseline gap-4">
          <span class="text-gray-500 text-sm w-24">Heading 1</span>
          <span class="text-3xl font-bold">Traffic Detection</span>
        </div>
        <div class="flex items-baseline gap-4">
          <span class="text-gray-500 text-sm w-24">Heading 2</span>
          <span class="text-xl font-semibold">Section Title</span>
        </div>
        <div class="flex items-baseline gap-4">
          <span class="text-gray-500 text-sm w-24">Heading 3</span>
          <span class="text-lg font-medium">Subsection</span>
        </div>
        <div class="flex items-baseline gap-4">
          <span class="text-gray-500 text-sm w-24">Body</span>
          <span class="text-base">Regular body text for descriptions and content.</span>
        </div>
        <div class="flex items-baseline gap-4">
          <span class="text-gray-500 text-sm w-24">Small</span>
          <span class="text-sm text-gray-400">Secondary text, labels, and captions.</span>
        </div>
        <div class="flex items-baseline gap-4">
          <span class="text-gray-500 text-sm w-24">Mono</span>
          <span class="font-mono text-sm">Code, values: 30fps, 1280x720</span>
        </div>
      </div>
    </section>

    <!-- Buttons Section -->
    <section class="mb-10">
      <h2 class="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">Buttons</h2>

      <div class="mb-6">
        <h3 class="text-sm font-medium text-gray-700 mb-3">Primary Actions</h3>
        <div class="flex flex-wrap gap-3">
          <Button label="Primary" icon="pi pi-check" size="normals" />
          <Button label="Secondary" icon="pi pi-cog" severity="secondary" />
          <Button label="Success" icon="pi pi-check-circle" severity="success" />
          <Button label="Warning" icon="pi pi-exclamation-triangle" severity="warning" />
          <Button label="Danger" icon="pi pi-trash" severity="danger" />
        </div>
      </div>

      <div class="mb-6">
        <h3 class="text-sm font-medium text-gray-700 mb-3">Outlined Variants</h3>
        <div class="flex flex-wrap gap-3">
          <Button label="Primary" icon="pi pi-check" outlined />
          <Button label="Secondary" icon="pi pi-cog" severity="secondary" outlined />
          <Button label="Success" icon="pi pi-check-circle" severity="success" outlined />
        </div>
      </div>

      <div class="mb-6">
        <h3 class="text-sm font-medium text-gray-700 mb-3">States</h3>
        <div class="flex flex-wrap gap-3">
          <Button label="Loading" icon="pi pi-spinner pi-spin" :loading="true" />
          <Button label="Disabled" icon="pi pi-ban" disabled />
          <Button icon="pi pi-plus" aria-label="Icon Only" />
        </div>
      </div>

      <div>
        <h3 class="text-sm font-medium text-gray-700 mb-3">Sizes</h3>
        <div class="flex flex-wrap items-center gap-3">
          <Button label="Small" size="small" />
          <Button label="Normal" />
          <Button label="Large" size="large" />
        </div>
      </div>
    </section>

    <!-- Form Elements Section -->
    <section class="mb-10">
      <h2 class="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">Form Elements</h2>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="space-y-4">
          <div>
            <label class="block text-sm text-gray-700 mb-1">Text Input</label>
            <InputText v-model="sampleText" placeholder="Enter value..." class="w-full" />
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">Number Input</label>
            <InputNumber v-model="sampleNumber" :min="0" :max="100" class="w-full" />
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">Slider</label>
            <Slider v-model="sampleSlider" :min="0" :max="100" class="w-full" />
            <span class="text-sm text-gray-500">Value: {{ sampleSlider }}</span>
          </div>
        </div>
        <div class="space-y-4">
          <div>
            <label class="block text-sm text-gray-400 mb-1">Dropdown</label>
            <Select v-model="sampleSelect" :options="selectOptions" placeholder="Select option" class="w-full" />
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">Checkbox</label>
            <div class="flex items-center gap-2">
              <Checkbox v-model="sampleCheck" :binary="true" inputId="check1" />
              <label for="check1">Enable feature</label>
            </div>
          </div>
          <div>
            <label class="block text-sm text-gray-400 mb-1">Toggle</label>
            <ToggleSwitch v-model="sampleToggle" />
          </div>
        </div>
      </div>
    </section>

    <!-- Panels Section -->
    <section class="mb-10">
      <h2 class="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">Panels & Cards</h2>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Panel header="Panel Title">
          <p class="text-sm">Panel content with standard padding and header styling.</p>
        </Panel>

        <Card>
          <template #title>Card Title</template>
          <template #content>
            <p class="text-sm">Card component for grouped content.</p>
          </template>
        </Card>
      </div>
    </section>

    <!-- Messages Section -->
    <section class="mb-10">
      <h2 class="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">Messages</h2>

      <div class="space-y-3">
        <Message severity="info" :closable="false">Informational message</Message>
        <Message severity="success" :closable="false">Success message</Message>
        <Message severity="warn" :closable="false">Warning message</Message>
        <Message severity="error" :closable="false">Error message</Message>
      </div>
    </section>

    <!-- Spacing Reference -->
    <section class="mb-10">
      <h2 class="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">Spacing</h2>
      <div class="flex items-end gap-4">
        <div class="text-center">
          <div class="w-4 h-4 bg-blue-500 mb-1"></div>
          <span class="text-xs text-gray-500">4px</span>
        </div>
        <div class="text-center">
          <div class="w-6 h-6 bg-blue-500 mb-1"></div>
          <span class="text-xs text-gray-500">8px</span>
        </div>
        <div class="text-center">
          <div class="w-8 h-8 bg-blue-500 mb-1"></div>
          <span class="text-xs text-gray-500">12px</span>
        </div>
        <div class="text-center">
          <div class="w-12 h-12 bg-blue-500 mb-1"></div>
          <span class="text-xs text-gray-500">16px</span>
        </div>
        <div class="text-center">
          <div class="w-16 h-16 bg-blue-500 mb-1"></div>
          <span class="text-xs text-gray-500">24px</span>
        </div>
        <div class="text-center">
          <div class="w-20 h-20 bg-blue-500 mb-1"></div>
          <span class="text-xs text-gray-500">32px</span>
        </div>
      </div>
    </section>

    <!-- Icons Reference -->
    <section>
      <h2 class="text-xl font-semibold mb-4 border-b border-gray-700 pb-2">Common Icons</h2>
      <div class="grid grid-cols-4 md:grid-cols-8 gap-4">
        <IconDemo icon="pi-video" name="Video" />
        <IconDemo icon="pi-camera" name="Camera" />
        <IconDemo icon="pi-chart-bar" name="Stats" />
        <IconDemo icon="pi-cog" name="Settings" />
        <IconDemo icon="pi-save" name="Save" />
        <IconDemo icon="pi-trash" name="Delete" />
        <IconDemo icon="pi-plus" name="Add" />
        <IconDemo icon="pi-check" name="Check" />
        <IconDemo icon="pi-times" name="Close" />
        <IconDemo icon="pi-refresh" name="Refresh" />
        <IconDemo icon="pi-play" name="Play" />
        <IconDemo icon="pi-pause" name="Pause" />
        <IconDemo icon="pi-map" name="Map" />
        <IconDemo icon="pi-eye" name="View" />
        <IconDemo icon="pi-pencil" name="Edit" />
        <IconDemo icon="pi-download" name="Download" />
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, h } from 'vue'
import { usePreset } from '@primevue/themes'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import InputNumber from 'primevue/inputnumber'
import Slider from 'primevue/slider'
import Select from 'primevue/select'
import Checkbox from 'primevue/checkbox'
import ToggleSwitch from 'primevue/toggleswitch'
import Panel from 'primevue/panel'
import Card from 'primevue/card'
import Message from 'primevue/message'

const sampleText = ref('')
const sampleNumber = ref(50)
const sampleSlider = ref(30)
const sampleSelect = ref(null)
const sampleCheck = ref(false)
const sampleToggle = ref(true)

const selectOptions = ['Option A', 'Option B', 'Option C']

const currentTheme = ref('MyPreset')

const setTheme = (themeName) => {
  const presets = window.__PRIMEVUE_PRESETS__
  if (presets && presets[themeName]) {
    usePreset(presets[themeName])
    currentTheme.value = themeName
  }
}

const ColorSwatch = {
  props: ['color', 'name', 'cssVar'],
  setup(props) {
    return () => h('div', { class: 'text-center' }, [
      h('div', {
        class: 'w-full h-6 rounded-lg mb-1 border border-gray-700',
        style: { backgroundColor: props.color }
      }),
      h('div', { class: 'text-sm font-small' }, props.name),
      h('div', { class: 'text-xs text-gray-500 font-mono' }, props.cssVar)
    ])
  }
}

const IconDemo = {
  props: ['icon', 'name'],
  setup(props) {
    return () => h('div', { class: 'text-center p-1 rounded-lg hover:bg-gray-800 transition-colors' }, [
      h('i', { class: ['pi', props.icon, 'text-xl mb-1 block'] }),
      h('span', { class: 'text-xs text-gray-500' }, props.name)
    ])
  }
}
</script>
