<script setup lang="ts">
// Root component — just provides page-level fade transition
</script>

<template>
  <RouterView v-slot="{ Component }">
    <Transition name="page-fade" mode="out-in">
      <component :is="Component" />
    </Transition>
  </RouterView>
</template>

<style>
/* ============================================================
   Page-level transition
   ⚠️ Safe to use opacity here — no backdrop-filter on page root
   ============================================================ */
.page-fade-enter-from,
.page-fade-leave-to  { opacity: 0; }
.page-fade-enter-active { transition: opacity 0.4s ease; }
.page-fade-leave-active  { transition: opacity 0.3s ease; }
</style>
