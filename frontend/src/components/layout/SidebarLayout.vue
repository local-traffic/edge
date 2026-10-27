<template>
  <div class="grid grid-cols-3  gap-4">
    <aside class="overflow-y-auto">
      <slot name="sidebar" />
    </aside>
    <main class="col-span-2 ">
      <slot name="content" />
    </main>
  </div>
</template>

<script setup>
// Simplified layout with Tailwind CSS utilities
</script>

<style scoped>
/* No custom CSS needed - using Tailwind utilities */
</style>
