import { ref } from 'vue'
import { parseApiError } from '@/utils/error'

export function useAsync<T>(fn: () => Promise<T>) {
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function execute() {
    loading.value = true
    error.value = null
    try {
      const result = await fn()
      return result
    } catch (err) {
      error.value = parseApiError(err)
      setTimeout(() => (error.value = null), 4000)
      throw err
    } finally {
      loading.value = false
    }
  }

  return { loading, error, execute }
}
