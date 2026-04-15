<script setup lang="ts">
defineProps<{
  message: string
}>()
</script>

<template>
  <p v-if="message" class="error-toast font-ui">{{ message }}</p>
</template>

<style scoped>
.error-toast {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(223, 74, 74, 0.9);
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 13px;
  z-index: 9999;
  letter-spacing: 1px;
  max-width: 80vw;
  text-align: center;
}
</style>
