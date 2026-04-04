/**
 * Parse API error responses into user-friendly Chinese messages.
 */
export function parseApiError(error: any): string {
  const data = error.response?.data

  // Pydantic 422 validation errors
  if (Array.isArray(data?.detail)) {
    return data.detail.map((e: any) => {
      const field = e.loc?.[e.loc.length - 1] || ''
      const fieldNames: Record<string, string> = {
        username: '用户名',
        password: '密码',
        name: '名称',
        message: '消息',
        save_name: '存档名',
        email: '邮箱',
      }
      const name = fieldNames[field] || field

      const messages: Record<string, string> = {
        string_too_short: `${name}至少需要 ${e.ctx?.min_length} 个字符`,
        string_too_long: `${name}不能超过 ${e.ctx?.max_length} 个字符`,
        string_pattern_mismatch: `${name}只能包含字母、数字、下划线和横杠`,
        value_error: `${name}格式不正确`,
      }
      return messages[e.type] || e.msg
    }).join('；')
  }

  // String error from backend
  if (typeof data?.detail === 'string') {
    const friendlyMessages: Record<string, string> = {
      'Username already registered': '该用户名已被注册',
      'Incorrect username or password': '用户名或密码错误',
      'Could not validate credentials': '登录已过期，请重新登录',
      'Subject not found': '科目不存在',
      'Course not found': '课程不存在',
      'Character not found': '角色不存在',
      'Teacher persona not found': '教师人格不存在',
      'Session not found': '会话不存在',
      'Save not found': '存档不存在',
      'Progress not found': '进度不存在',
      'Access denied': '访问被拒绝',
    }
    return friendlyMessages[data.detail] || data.detail
  }

  // Network error
  if (!error.response) return '网络连接失败，请检查网络'

  // Rate limit
  if (error.response?.status === 429) return '操作太频繁，请稍后再试'

  return '操作失败，请重试'
}
