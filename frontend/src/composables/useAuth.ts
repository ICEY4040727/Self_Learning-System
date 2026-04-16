/**
 * Auth Composable
 * Issue #29: 统一 API 调用层
 */
import { ref } from 'vue'
import { authApi } from '@/api/auth'
import type { LoginRequest, RegisterRequest } from '@/types'

export function useAuth() {
  const user = ref<unknown>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function login(data: LoginRequest) {
    loading.value = true
    error.value = null
    try {
      const result = await authApi.login(data)
      // 假设登录成功后返回用户信息或 token
      user.value = result
      return result
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '登录失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function register(data: RegisterRequest) {
    loading.value = true
    error.value = null
    try {
      const result = await authApi.register(data)
      return result
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '注册失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchCurrentUser() {
    loading.value = true
    error.value = null
    try {
      user.value = await authApi.me()
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : '获取用户信息失败'
      user.value = null
    } finally {
      loading.value = false
    }
  }

  function logout() {
    user.value = null
    localStorage.removeItem('token')
  }

  return {
    user,
    loading,
    error,
    login,
    register,
    fetchCurrentUser,
    logout,
  }
}
