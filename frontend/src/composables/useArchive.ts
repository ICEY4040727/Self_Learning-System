/**
 * Archive Composable
 * Issue #29: 统一 API 调用层
 */
import { ref } from 'vue'
import { archiveApi } from '@/api/archive'

export function useArchive() {
  const diaries = ref<unknown[]>([])
  const sessions = ref<unknown[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchDiaries() {
    loading.value = true
    error.value = null
    try {
      diaries.value = await archiveApi.getDiaries()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '获取日记失败'
      console.error('fetchDiaries error:', e)
    } finally {
      loading.value = false
    }
  }

  async function createDiary(content: string) {
    try {
      const newDiary = await archiveApi.createDiary(content)
      diaries.value.unshift(newDiary)
      return newDiary
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '创建日记失败'
      throw e
    }
  }

  async function fetchSessions() {
    loading.value = true
    error.value = null
    try {
      sessions.value = await archiveApi.getSessions()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '获取会话列表失败'
      console.error('fetchSessions error:', e)
    } finally {
      loading.value = false
    }
  }

  async function getEmotionTrajectory(sessionId: number) {
    try {
      return await archiveApi.getEmotionTrajectory(sessionId)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '获取情感轨迹失败'
      throw e
    }
  }

  return {
    diaries,
    sessions,
    loading,
    error,
    fetchDiaries,
    createDiary,
    fetchSessions,
    getEmotionTrajectory,
  }
}
