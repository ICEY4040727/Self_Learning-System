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

  // ── Textbook / Course Generation (Phase 2C) ──────────────────

  /**
   * 上传教材到课程
   */
  uploadTextbook: (courseId: number, file: File, onProgress?: (pct: number) => void) => {
    const form = new FormData()
    form.append('file', file)
    return client.post(`/courses/${courseId}/textbooks`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (onProgress && e.total) onProgress(Math.round((e.loaded / e.total) * 100))
      },
    }).then(res => res.data)
  },

  /**
   * 列出课程的教材
   */
  listTextbooks: (courseId: number) =>
    client.get(`/courses/${courseId}/textbooks`).then(res => res.data),

  /**
   * 删除教材
   */
  deleteTextbook: (courseId: number, textbookId: number) =>
    client.delete(`/courses/${courseId}/textbooks/${textbookId}`).then(res => res.data),

  /**
   * 基于教材生成课程结构
   */
  generateCourse: (courseId: number) =>
    client.post(`/courses/${courseId}/generate`).then(res => res.data),

  /**
   * 获取课程进度（课程列表）
   */
  getProgress: (courseId: number) =>
    client.get(`/courses/${courseId}/progress`).then(res => res.data),

  /**
   * 推进到下一课
   */
  advanceLesson: (courseId: number) =>
    client.post(`/courses/${courseId}/advance`).then(res => res.data),

  /**
   * 获取课程精通度
   */
  getMastery: (courseId: number) =>
    client.get(`/courses/${courseId}/mastery`).then(res => res.data),

  /**
   * 获取学习者画像 (dimension_scores, strengths, weaknesses, learning_stats)
   */
  getLearnerProfile: (worldId: number) =>
    client.get(`/worlds/${worldId}/learner_profile`).then(res => res.data),
}
