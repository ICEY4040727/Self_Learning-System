<template>
  <RouterView v-slot="{ Component }">
    <Transition name="page-fade" mode="out-in">
      <component :is="Component" />
    </Transition>
  </RouterView>
</template>

<script setup lang="ts">
</script>

<style>
.page-fade-enter-from,
.page-fade-leave-to {
  opacity: 0;
}

.page-fade-enter-active {
  transition: opacity var(--transition-page, 0.4s ease);
}

.page-fade-leave-active {
  transition: opacity 0.3s ease;
}
</style>
