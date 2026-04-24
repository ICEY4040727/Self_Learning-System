/**
 * Auth API Module
 * Issue #29: 统一 API 调用层
 */
import client from './client'

export const authApi = {
  /**
   * 用户登录（OAuth2 password flow — requires FormData）
   */
  login: (username: string, password: string) => {
    const formData = new FormData()
    formData.append('username', username)
    formData.append('password', password)
    return client.post('/auth/login', formData).then(res => res.data)
  },

  /**
   * 用户注册
   */
  register: (data: { username: string; password: string }) =>
    client.post('/auth/register', data).then(res => res.data),

  /**
   * 获取当前用户信息
   */
  me: () =>
    client.get('/auth/me').then(res => res.data),
}
