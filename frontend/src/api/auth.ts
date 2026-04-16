/**
 * Auth API Module
 * Issue #29: 统一 API 调用层
 */
import client from './client'
import type { LoginRequest, RegisterRequest } from '@/types'

export const authApi = {
  /**
   * 用户登录
   */
  login: (data: LoginRequest) =>
    client.post('/auth/login', data).then(res => res.data),

  /**
   * 用户注册
   */
  register: (data: RegisterRequest) =>
    client.post('/auth/register', data).then(res => res.data),

  /**
   * 获取当前用户信息
   */
  me: () =>
    client.get('/auth/me').then(res => res.data),
}
