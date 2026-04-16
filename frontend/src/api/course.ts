/**
 * Course API Module
 * Issue #29: 统一 API 调用层
 */
import client from './client'

export const courseApi = {
  /**
   * 获取课程详情
   */
  get: (courseId: number) =>
    client.get(`/courses/${courseId}`).then(res => res.data),

  /**
   * 获取课程的导师列表
   */
  getSages: (courseId: number) =>
    client.get(`/courses/${courseId}/sages`).then(res => res.data),

  /**
   * 获取课程的会话列表
   */
  getSessions: (courseId: number) =>
    client.get(`/courses/${courseId}/sessions`).then(res => res.data),

  /**
   * 获取课程的记忆事实
   */
  getMemoryFacts: (courseId: number, statsOnly = true) =>
    client.get(`/courses/${courseId}/memory-facts?stats_only=${statsOnly}`).then(res => res.data),

  /**
   * 开始学习会话
   */
  start: (courseId: number, sageId: number) =>
    client.post(`/courses/${courseId}/start`, { sage_id: sageId }).then(res => res.data),
}
