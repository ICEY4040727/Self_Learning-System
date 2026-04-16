<template>
  <div id="app">
    <ToastContainer />
    <router-view v-slot="{ Component }">
      <Transition name="page-fade">
        <component :is="Component" />
      </Transition>
    </router-view>
  </div>
</template>

<script setup lang="ts">
/**
 * Root component
 * Issue #27 + #33: 统一 Toast 通知系统
 */
import ToastContainer from '@/components/ToastContainer.vue'
</script>

<style>
#app {
  min-height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
}
</style>
