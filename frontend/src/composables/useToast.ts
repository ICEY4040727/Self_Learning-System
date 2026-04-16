/**
 * Toast Composable
 * Issue #27 + #33: 统一 Toast 通知系统
 */
import { ref } from 'vue'

export interface Toast {
  id: number
  message: string
  type: 'error' | 'success' | 'warning'
  duration: number
}

// 全局 toast 状态
const toasts = ref<Toast[]>([])

export function useToast() {
  function show(
    message: string,
    type: Toast['type'] = 'error',
    duration: number = 4000
  ): number {
    const id = Date.now() + Math.random()
    toasts.value.push({ id, message, type, duration })
    
    // 自动移除
    if (duration > 0) {
      setTimeout(() => {
        remove(id)
      }, duration)
    }
    
    return id
  }

  function remove(id: number) {
    const index = toasts.value.findIndex(t => t.id === id)
    if (index > -1) {
      toasts.value.splice(index, 1)
    }
  }

  // 便捷方法
  function error(message: string, duration = 4000) {
    return show(message, 'error', duration)
  }

  function success(message: string, duration = 4000) {
    return show(message, 'success', duration)
  }

  function warning(message: string, duration = 4000) {
    return show(message, 'warning', duration)
  }

  return {
    toasts,
    show,
    remove,
    error,
    success,
    warning
  }
}
