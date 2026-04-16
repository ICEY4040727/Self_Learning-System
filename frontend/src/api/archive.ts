/**
 * Archive API Module
 * Issue #29: 统一 API 调用层
 */
import client from './client'

export const archiveApi = {
  /**
   * 获取学习日记列表
   */
  getDiaries: () =>
    client.get('/learning_diary').then(res => res.data),

  /**
   * 创建学习日记
   */
  createDiary: (content: string) =>
    client.post('/learning_diary', { content }).then(res => res.data),

  /**
   * 获取进度数据
   */
  getProgress: () =>
    client.get('/progress').then(res => res.data),

  /**
   * 获取会话列表
   */
  getSessions: () =>
    client.get('/sessions').then(res => res.data),

  /**
   * 获取情感轨迹
   */
  getEmotionTrajectory: (sessionId: number) =>
    client.get(`/sessions/${sessionId}/emotion_trajectory`).then(res => res.data),

  /**
   * 获取课程列表
   */
  getCourses: () =>
    client.get('/courses').then(res => res.data),

  /**
   * 获取世界列表（归档视图用）
   */
  getWorlds: () =>
    client.get('/worlds').then(res => res.data),

  /**
   * 获取角色列表（归档视图用）
   */
  getCharacters: () =>
    client.get('/characters').then(res => res.data),
}
