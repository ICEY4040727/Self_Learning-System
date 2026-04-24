/**
 * Courses Composable
 * Issue #29: 统一 API 调用层
 */
import { ref } from 'vue'
import { courseApi } from '@/api/course'

export function useCourses() {
  const course = ref<unknown>(null)
  const sages = ref<unknown[]>([])
  const sessions = ref<unknown[]>([])
  const memoryStats = ref<unknown>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchCourse(courseId: number) {
    loading.value = true
    error.value = null
    try {
      course.value = await courseApi.get(courseId)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '获取课程失败'
      console.error('fetchCourse error:', e)
    } finally {
      loading.value = false
    }
  }

  async function fetchSages(courseId: number) {
    try {
      sages.value = await courseApi.getSages(courseId)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '获取导师列表失败'
      console.error('fetchSages error:', e)
    }
  }

  async function fetchSessions(courseId: number) {
    try {
      sessions.value = await courseApi.getSessions(courseId)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '获取会话列表失败'
      console.error('fetchSessions error:', e)
    }
  }

  async function fetchMemoryFacts(courseId: number, statsOnly = true) {
    try {
      memoryStats.value = await courseApi.getMemoryFacts(courseId, statsOnly)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '获取记忆事实失败'
      console.error('fetchMemoryFacts error:', e)
    }
  }

  async function startCourse(courseId: number, sageId: number) {
    try {
      return await courseApi.start(courseId, sageId)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '开始课程失败'
      throw e
    }
  }

  return {
    course,
    sages,
    sessions,
    memoryStats,
    loading,
    error,
    fetchCourse,
    fetchSages,
    fetchSessions,
    fetchMemoryFacts,
    startCourse,
  }
}
