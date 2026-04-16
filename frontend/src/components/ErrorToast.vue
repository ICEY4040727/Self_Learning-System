<script setup lang="ts">
/**
 * ErrorToast Component
 * Issue #27 + #33: 统一 Toast 通知系统
 */
import { ref, watch } from 'vue'

const props = defineProps<{
  message: string
  type?: 'error' | 'success' | 'warning'
  duration?: number
}>()

const visible = ref(true)

watch(() => props.message, (newMsg) => {
  if (newMsg) {
    visible.value = true
    // 自动消失
    if (props.duration && props.duration > 0) {
      setTimeout(() => {
        visible.value = false
      }, props.duration)
    }
  }
}, { immediate: true })

const emit = defineEmits<{
  close: []
}>()

const typeColors = {
  error: 'rgba(223, 74, 74, 0.9)',
  success: 'rgba(34, 197, 94, 0.9)',
  warning: 'rgba(251, 191, 36, 0.9)'
}
</script>

<template>
  <Transition name="toast">
    <p 
      v-if="visible" 
      class="error-toast font-ui"
      :style="{ background: type ? typeColors[type] : typeColors.error }"
      @click="emit('close')"
    >
      {{ message }}
    </p>
  </Transition>
</template>

<style scoped>
.error-toast {
  padding: 8px 14px;
  border-radius: 6px;
  font-size: 13px;
  letter-spacing: 1px;
  max-width: 80vw;
  text-align: center;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}

.toast-enter-from {
  opacity: 0;
  transform: translateY(-20px);
}

.toast-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}
</style>
