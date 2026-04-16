/**
 * Courses Composable
 * Issue #29: 统一 API 调用层
 */
import { ref } from 'vue'
import { courseApi } from '@/api/course'

export function useCourses() {
  const course = ref<unknown>(null)
  const courses = ref<unknown[]>([])
  const sessions = ref<unknown[]>([])
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

  async function fetchCourses() {
    loading.value = true
    error.value = null
    try {
      courses.value = await courseApi.get(courseId)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '获取课程列表失败'
      console.error('fetchCourses error:', e)
    } finally {
      loading.value = false
    }
  }

  async function startCourse(courseId: number, sageId: number) {
    try {
      const result = await courseApi.start(courseId, sageId)
      return result
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '开始课程失败'
      throw e
    }
  }

  async function getMemoryFacts(courseId: number, statsOnly = true) {
    try {
      return await courseApi.getMemoryFacts(courseId, statsOnly)
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '获取记忆事实失败'
      throw e
    }
  }

  return {
    course,
    courses,
    sessions,
    loading,
    error,
    fetchCourse,
    fetchCourses,
    startCourse,
    getMemoryFacts,
  }
}
