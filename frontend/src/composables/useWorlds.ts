/**
 * Worlds Composable
 * Issue #29 + #32: 统一 API 调用层
 */
import { ref } from 'vue'
import { worldApi } from '@/api/world'
import type { World } from '@/types'

export function useWorlds() {
  const worlds = ref<World[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchWorlds() {
    loading.value = true
    error.value = null
    try {
      worlds.value = await worldApi.list()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '获取世界列表失败'
      console.error('fetchWorlds error:', e)
    } finally {
      loading.value = false
    }
  }

  async function createWorld(data: { name: string; description?: string }) {
    try {
      const newWorld = await worldApi.create(data)
      worlds.value.push(newWorld)
      return newWorld
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '创建世界失败'
      throw e
    }
  }

  async function deleteWorld(id: number) {
    try {
      await worldApi.delete(id)
      worlds.value = worlds.value.filter(w => w.id !== id)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '删除世界失败'
      throw e
    }
  }

  async function updateWorld(id: number, data: Partial<World>) {
    try {
      const updated = await worldApi.update(id, data)
      const index = worlds.value.findIndex(w => w.id === id)
      if (index !== -1) {
        worlds.value[index] = updated
      }
      return updated
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '更新世界失败'
      throw e
    }
  }

  return {
    worlds,
    loading,
    error,
    fetchWorlds,
    createWorld,
    deleteWorld,
    updateWorld,
  }
}
